import numpy as np
import torch

from memory.policy.standard import PolicyMemory

class EmbeddingPolicyMemory(PolicyMemory):
    def __init__(self, datas):
        if datas is None :
            self.available_actions = []
            super().__init__()

        else:
            states, actions, rewards, dones, next_states, available_actions = datas
            self.available_actions = available_actions
            
            super().__init__((states, actions, rewards, dones, next_states))

    def __len__(self):
        return len(self.dones)

    def __getitem__(self, idx):
        states, actions, rewards, dones, next_states = super().__getitem__(idx)
        return states, actions, rewards, dones, next_states, torch.tensor(self.available_actions[idx])

    def save_obs(self, state, action, reward, done, next_state, available_action):
        super().save_obs(state, reward, action, done, next_state)
        self.available_actions.append(available_action)

    def save_replace_all(self, states, actions, rewards, dones, next_states, available_actions):
        super().save_all(states, rewards, actions, dones, next_states)
        self.available_actions = available_actions

    def save_all(self, states, actions, rewards, dones, next_states, available_actions):
        super().save_all(states, actions, rewards, dones, next_states)
        self.available_actions    += available_actions

    def get_all_items(self):
        states, actions, rewards, dones, next_states = super().get_all_items()
        return states, actions, rewards, dones, next_states, self.available_actions

    def get_ranged_items(self, start_position = 0, end_position = None):   
        if end_position is not None or end_position == -1:
            available_actions   = self.available_actions[start_position:end_position + 1]
        else:
            available_actions   = self.available_actions[start_position:]

        states, actions, rewards, dones, next_states = super().get_ranged_items()
        return states, actions, rewards, dones, next_states, available_actions
        
    def clear_memory(self):
        super().clear_memory()
        del self.available_actions[:]
