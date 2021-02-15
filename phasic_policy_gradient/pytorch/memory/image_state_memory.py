import torch
import numpy as np
from torch.utils.data import Dataset

from memory.list_memory import ListMemory

class ImageStateMemory(ListMemory):
    def __init__(self, datas = None):
        if datas is None :
            self.images         = []
            self.next_images    = []
            super().__init__()

        else:
            images, states, actions, rewards, dones, next_images, next_states = datas
            self.images         = images
            self.next_images    = next_images
            
            super().__init__((states, actions, rewards, dones, next_states))

    def __len__(self):
        return len(self.dones)

    def __getitem__(self, idx):
        states, actions, rewards, dones, next_states = super().__getitem__(idx)
        return np.array(self.images[idx], dtype = np.float32), states, actions, rewards, dones, np.array(self.next_images[idx], dtype = np.float32), next_states

    def save_eps(self, image, state, action, reward, done, next_image, next_state):
        super().save_eps(state, action, reward, done, next_state)
        self.images.append(image)
        self.next_images.append(next_image)

    def save_replace_all(self, images, states, actions, rewards, dones, next_images, next_states):
        super().save_all(states, actions, rewards, dones, next_states)
        self.images         = images
        self.next_images    = next_images

    def save_all(self, images, states, actions, rewards, dones, next_images, next_states):
        super().save_all(states, actions, rewards, dones, next_states)
        self.images         += images
        self.next_images    += next_images

    def get_all_items(self):
        states, actions, rewards, dones, next_states = super().get_all_items()
        return self.images, states, actions, rewards, dones, self.next_images, next_states

    def clear_memory(self):
        super().clear_memory()
        del self.images[:]
        del self.next_images[:]