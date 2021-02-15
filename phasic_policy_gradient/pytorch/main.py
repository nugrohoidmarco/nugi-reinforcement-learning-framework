import gym
import random
import numpy as np
import torch
import os
import ray

# from torch.utils.tensorboard import SummaryWriter

from eps_runner.sync import SyncRunner
from executor.sync import SyncExecutor

from agent.agent import Agent
from distribution.basic import BasicContinous
from loss.joint_aux import JointAux
from loss.truly_ppo import TrulyPPO
from model.TanhNN import Policy_Model, Value_Model
from environment.wrapper.vector_gym_env import VectorEnv

# from environment.custom.carla_env import CarlaEnv
""" from mlagents_envs.registry import default_registry
from mlagents_envs.environment import UnityEnvironment """
#from gym_unity.envs import UnityToGymWrapper

############## Hyperparameters ##############

load_weights            = False # If you want to load the agent, set this to True
save_weights            = False # If you want to save the agent, set this to True
training_mode           = True # If you want to train the agent, set this to True. But set this otherwise if you only want to test it
use_gpu                 = True
reward_threshold        = 495 # Set threshold for reward. The learning will stop if reward has pass threshold. Set none to sei this off

render                  = True # If you want to display the image. Turn this off if you run this in Google Collab
n_saved                 = 1

n_plot_batch            = 1 # How many episode you want to plot the result
n_iteration             = 1000000 # How many episode you want to run
n_update                = 1024 # How many episode before you update the Policy
n_aux_update            = 5

policy_kl_range         = 0.03
policy_params           = 5
value_clip              = 5.0
entropy_coef            = 0.0
vf_loss_coef            = 1.0
batch_size              = 32
PPO_epochs              = 10
Aux_epochs              = 10
action_std              = 1.0
gamma                   = 0.99
lam                     = 0.95
learning_rate           = 2.5e-4

params_max              = 1.0
params_min              = 0.25
params_subtract         = 0.001
params_dynamic          = False
max_action              = None

folder                  = 'weights/carla'
env                     = [gym.make('BipedalWalker-v3') for _ in range(2)] # gym.make('BipedalWalker-v3') # CarlaEnv(im_height = 240, im_width = 240, im_preview = False, max_step = 512) # [gym.make(env_name) for _ in range(2)] # CarlaEnv(im_height = 240, im_width = 240, im_preview = False, seconds_per_episode = 3 * 60) # [gym.make(env_name) for _ in range(2)] # gym.make(env_name) # [gym.make(env_name) for _ in range(2)]
#env                     = UnityEnvironment(file_name=None, seed=1)
#env                     = UnityToGymWrapper(env)

Policy_or_Actor_Model   = Policy_Model
Value_or_Critic_Model   = Value_Model
Distribution            = BasicContinous
Runner                  = SyncRunner
Executor                = SyncExecutor
Policy_loss             = TrulyPPO
Aux_loss                = JointAux
Wrapper                 = VectorEnv(env)

state_dim               = None
action_dim              = None

#####################################################################################################################################################

random.seed(20)
np.random.seed(20)
torch.manual_seed(20)
os.environ['PYTHONHASHSEED'] = str(20)

if state_dim is None:
    state_dim = Wrapper.get_obs_dim()
print('state_dim: ', state_dim)

if Wrapper.is_discrete():  
    print('discrete')
else:
    print('continous')

if action_dim is None:
    action_dim = Wrapper.get_action_dim()
print('action_dim: ', action_dim)

agent = Agent(Policy_or_Actor_Model, Value_or_Critic_Model, state_dim, action_dim, Distribution, training_mode, policy_kl_range, policy_params, 
    value_clip, entropy_coef, vf_loss_coef, batch_size, PPO_epochs, Aux_epochs, gamma, lam, learning_rate, folder, use_gpu, Policy_loss, Aux_loss)

ray.init()
runner = [Runner.remote(i_env, render, training_mode, n_update, Wrapper.is_discrete(), agent, max_action, None, n_plot_batch) for i_env in env]

executor = Executor(agent, Wrapper, n_iteration, runner, reward_threshold, save_weights = False, n_plot_batch = 100, render = True, training_mode = True, n_update = 1024, n_aux_update = 10, 
    n_saved = 10, max_action = 1.0, load_weights = False)

executor.execute()