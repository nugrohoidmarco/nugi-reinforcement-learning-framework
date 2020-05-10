from flask import Flask, jsonify, request
from flask_socketio import SocketIO, send, emit
from datetime import datetime
import numpy as np
import requests

from memory.on_policy_impala_memory import OnMemoryImpala

############## Hyperparameters ##############
render      = False # If you want to display the image. Turn this off if you run this in Google Collab
n_update    = 1024 # How many episode before you update the Policy
state_dim   = 24 #8
action_dim  = 4 #2
#############################################
app                         = Flask(__name__)
app.config['SECRET_KEY']    = 'vnkdjnfjknfl1232#'
socketio                    = SocketIO(app)
memory                      = OnMemoryImpala()

print('Agent has been initialized')
############################################# 

@app.route('/trajectory', methods=['POST'])
def save_trajectory():
    global memory
    data = request.get_json()    

    states              = data['states']
    actions             = data['actions']
    rewards             = data['rewards']
    dones               = data['dones']
    next_states         = data['next_states']
    worker_action_datas = data['worker_action_datas']

    for s, a, r, d, ns, wad in zip(states, actions, rewards, dones, next_states, worker_action_datas):            
        memory.save_eps(s, a, r, d, ns, wad)

    if len(memory) >= n_update:
        socketio.emit('update_model')

    data = {
        'success': True
    }

    return jsonify(data)

@app.route('/trajectory', methods=['GET'])
def send_trajectory():
    memory = OnMemoryImpala()

    states              = []
    actions             = []
    rewards             = []
    dones               = []
    next_states         = []
    worker_action_datas = []

    for i in range(len(memory)):
        state, action, reward, done, next_state, worker_action_data = memory.pop(0)

        states.append(state)
        actions.append(action)
        rewards.append(reward)
        dones.append(done)
        next_states.append(next_state)
        worker_action_datas.append(worker_action_data)
    
    data = {
        'states'                : states,
        'actions'               : actions,
        'rewards'               : rewards,        
        'dones'                 : dones,
        'next_states'           : next_states,
        'worker_action_datas'   : worker_action_datas
    }

    return jsonify(data)

@app.route('/test')
def test():
    return 'test'

if __name__ == '__main__':
    print('Run..')
    socketio.run(app)
#app.run(host = '0.0.0.0', port = 8010, debug = True, threaded = True)