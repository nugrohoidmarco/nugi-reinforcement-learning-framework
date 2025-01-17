import gym
import random
import numpy as np
import torch
import os

from torch.utils.tensorboard import SummaryWriter
from torch.optim.adam import Adam

from nugi_rl.eps_runner.single_step.single_step_runner import SingleStepRunner
from nugi_rl.train_executor.executor import Executor
from nugi_rl.agent.standard.sac import AgentSAC
from nugi_rl.distribution.tanh_clipped_continous import TanhClippedContinous
from nugi_rl.environment.wrapper.gym_wrapper import GymWrapper
from nugi_rl.loss.sac.q_loss import QLoss
from nugi_rl.loss.sac.policy_loss import PolicyLoss
from nugi_rl.loss.sac.value_loss import ValueLoss
from nugi_rl.model.sac.TanhStdNN import Policy_Model, Q_Model, Value_Model
from nugi_rl.memory.policy.standard import PolicyMemory

from nugi_rl.helpers.pytorch_utils import set_device

############## Hyperparameters ##############

load_weights            = False # If you want to load the agent, set this to True
save_weights            = False # If you want to save the agent, set this to True
is_training_mode        = True # If you want to train the agent, set this to True. But set this otherwise if you only want to test it
is_save_memory          = True
use_gpu                 = True
render                  = True # If you want to display the image. Turn this off if you run this in Google Collab
reward_threshold        = 495 # Set threshold for reward. The learning will stop if reward has pass threshold. Set none to sei this off

n_memory                = 102400
n_iteration             = 1000000
n_plot_batch            = 1
soft_tau                = 0.995
n_saved                 = 1
epochs                  = 1
batch_size              = 32
action_std              = 1.0
learning_rate           = 3e-4
alpha                   = 0.2

folder                  = 'weights/carla'
env                     = gym.make('BipedalWalker-v3') # gym.make('BipedalWalker-v3') # gym.make('BipedalWalker-v3') for _ in range(2)] # CarlaEnv(im_height = 240, im_width = 240, im_preview = False, max_step = 512) # [gym.make(env_name) for _ in range(2)] # CarlaEnv(im_height = 240, im_width = 240, im_preview = False, seconds_per_episode = 3 * 60) # [gym.make(env_name) for _ in range(2)] # gym.make(env_name) # [gym.make(env_name) for _ in range(2)]

state_dim           = None
action_dim          = None
max_action          = 1

#####################################################################################################################################################

random.seed(20)
np.random.seed(20)
torch.manual_seed(20)
os.environ['PYTHONHASHSEED'] = str(20)

environment         = GymWrapper(env)

policy_dist         = TanhClippedContinous(use_gpu)
memory              = PolicyMemory(capacity = n_memory)

q_loss              = QLoss(policy_dist)
policy_loss         = PolicyLoss(policy_dist, alpha = alpha)
value_loss          = ValueLoss(policy_dist, alpha = alpha)

policy              = Policy_Model(state_dim, action_dim, use_gpu).float().to(set_device(use_gpu))
soft_q1             = Q_Model(state_dim, action_dim).float().to(set_device(use_gpu))
soft_q2             = Q_Model(state_dim, action_dim).float().to(set_device(use_gpu))
value               = Value_Model(state_dim).float().to(set_device(use_gpu))

policy_optimizer    = Adam(list(policy.parameters()), lr = learning_rate)        
soft_q_optimizer    = Adam(list(soft_q1.parameters()) + list(soft_q2.parameters()), lr = learning_rate)
value_optimizer     = Adam(list(value.parameters()), lr = learning_rate)

agent = AgentSAC(soft_q1, soft_q2, policy, value, state_dim, action_dim, policy_dist, q_loss, policy_loss, value_loss, memory, 
        soft_q_optimizer, policy_optimizer, value_optimizer, is_training_mode, batch_size, epochs, 
        soft_tau, folder, use_gpu)
                    
runner      = SingleStepRunner(agent, environment, is_save_memory, render, environment.is_discrete(), max_action, SummaryWriter(), n_plot_batch) # [Runner.remote(i_env, render, training_mode, n_update, Wrapper.is_discrete(), agent, max_action, None, n_plot_batch) for i_env in env]
executor    = Executor(agent, n_iteration, runner, save_weights, n_saved, load_weights, is_training_mode)

if state_dim is None:
    state_dim = environment.get_obs_dim()
print('state_dim: ', state_dim)

if environment.is_discrete():
    print('discrete')
else:
    print('continous')

if action_dim is None:
    action_dim = environment.get_action_dim()
print('action_dim: ', action_dim)

executor.execute()