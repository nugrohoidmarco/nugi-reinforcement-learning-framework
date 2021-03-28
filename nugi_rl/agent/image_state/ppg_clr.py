import copy

import torch
import torchvision.transforms as transforms
from torch.utils.data import DataLoader

from helpers.pytorch_utils import set_device, to_numpy, to_tensor
from agent.standard.ppg import AgentPPG

class AgentImageStatePPGClr(AgentPPG):
    def __init__(self, projector, cnn, policy, value, state_dim, action_dim, distribution, ppo_loss, aux_ppg_loss, aux_clr_loss, ppo_memory, aux_ppg_memory, aux_clr_memory,
            ppo_optimizer, aux_ppg_optimizer, aux_clr_optimizer, PPO_epochs = 10, Aux_epochs = 10, aux_clr_epochs = 10, n_aux_update = 10, is_training_mode = True, policy_kl_range = 0.03, 
            policy_params = 5, value_clip = 1.0, entropy_coef = 0.0, vf_loss_coef = 1.0, batch_size = 32,  folder = 'model', use_gpu = True):

        super().__init__(policy, value, state_dim, action_dim, distribution, ppo_loss, aux_ppg_loss, ppo_memory, aux_ppg_memory, 
            ppo_optimizer, aux_ppg_optimizer, PPO_epochs, Aux_epochs, n_aux_update, is_training_mode, policy_kl_range, 
            policy_params, value_clip, entropy_coef, vf_loss_coef, batch_size,  folder, use_gpu)

        self.cnn                = cnn
        self.projector          = projector

        self.aux_clrLoss        = aux_clr_loss
        self.aux_clr_memory     = aux_clr_memory
        self.aux_clr_optimizer  = aux_clr_optimizer
        self.aux_clr_scaler     = torch.cuda.amp.GradScaler()
        self.aux_clr_epochs     = aux_clr_epochs

        self.trans  = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))
        ])

    def _training_ppo(self, images, states, actions, rewards, dones, next_images, next_states):
        self.ppo_optimizer.zero_grad()
        with torch.cuda.amp.autocast():
            res                 = self.cnn(images)
            action_datas, _     = self.policy(res, states)
            values              = self.value(res, states)

            old_action_datas, _ = self.policy_old(res, states, True)
            old_values          = self.value_old(res, states, True)

            next_res            = self.cnn(next_images, True)
            next_values         = self.value(next_res, next_states, True)

            loss = self.ppoLoss.compute_loss(action_datas, old_action_datas, values, old_values, next_values, actions, rewards, dones)
        
        self.ppo_scaler.scale(loss).backward()
        self.ppo_scaler.step(self.ppo_optimizer)
        self.ppo_scaler.update()

    def _training_aux_ppg(self, images, states):
        self.aux_ppg_optimizer.zero_grad()        
        with torch.cuda.amp.autocast():
            res                     = self.cnn(images, True)

            returns                 = self.value(res, states, True)
            old_action_datas, _     = self.policy_old(res, states, True)

            action_datas, values    = self.policy(res, states)            

            loss = self.auxLoss.compute_loss(action_datas, old_action_datas, values, returns)

        self.auxppg_scaler.scale(loss).backward()
        self.auxppg_scaler.step(self.aux_ppg_optimizer)
        self.auxppg_scaler.update()

    def _training_aux_clr(self, first_images, second_images):
        self.aux_clr_optimizer.zero_grad()

        with torch.cuda.amp.autocast():
            out1        = self.cnn(first_images)
            encoded1    = self.projector(out1)

            out2        = self.cnn(second_images)
            encoded2    = self.projector(out2)

            loss = (self.aux_clrLoss.compute_loss(encoded1, encoded2) + self.aux_clrLoss.compute_loss(encoded2, encoded1)) / 2.0

        self.aux_clr_scaler.scale(loss).backward()
        self.aux_clr_scaler.step(self.aux_clr_optimizer)
        self.aux_clr_scaler.update()

    def _update_policy(self):
        dataloader = DataLoader(self.ppo_memory, self.batch_size, shuffle = False, num_workers = 4)

        for _ in range(self.ppo_epochs):       
            for images, states, actions, rewards, dones, next_images, next_states in dataloader: 
                self._training_ppo(images.float().to(self.device), states.float().to(self.device), actions.float().to(self.device), 
                    rewards.float().to(self.device), dones.float().to(self.device), next_images.float().to(self.device), next_states.float().to(self.device))

        images, states, _, _, _, _, _ = self.ppo_memory.get_all_items()
        self.aux_ppg_memory.save_all(images, states)
        self.ppo_memory.clear_memory()

        self.policy_old.load_state_dict(self.policy.state_dict())
        self.value_old.load_state_dict(self.value.state_dict())

    def _update_aux_ppg(self):
        dataloader  = DataLoader(self.aux_ppg_memory, self.batch_size, shuffle = False, num_workers = 4)

        for _ in range(self.aux_ppg_epochs):       
            for images, states in dataloader:
                self._training_aux_ppg(images.float().to(self.device), states.float().to(self.device))

        images, _ = self.aux_ppg_memory.get_all_items()
        self.aux_clr_memory.save_all(images)
        self.aux_ppg_memory.clear_memory()

        self.policy_old.load_state_dict(self.policy.state_dict())

    def _update_aux_clr(self):
        dataloader  = DataLoader(self.aux_clr_memory, self.batch_size, shuffle = True, num_workers = 4)

        for _ in range(self.aux_clr_epochs):
            for first_images, second_images in dataloader:
                self._training_aux_clr(first_images.float().to(self.device), second_images.float().to(self.device))

        self.aux_clr_memory.clear_memory()

    def update(self):
        self._update_policy()
        self.i_update += 1

        if self.i_update % self.n_aux_update == 0:
            self._update_aux_ppg()
            self._update_aux_clr()
            self.i_update = 0

    def save_memory(self, policy_memory):
        images, states, actions, rewards, dones, next_images, next_states = policy_memory.get_all_items()
        self.ppo_memory.save_all(images, states, actions, rewards, dones, next_images, next_states)

    def act(self, image, state):
        image, state        = self.trans(image).unsqueeze(0).to(self.device), torch.FloatTensor(state).unsqueeze(0).to(self.device)
        
        res                 = self.cnn(image)
        action_datas, _     = self.policy(res, state)
        
        if self.is_training_mode:
            action = self.distribution.sample(action_datas)
        else:
            action = self.distribution.deterministic(action_datas)
              
        return to_numpy(action, self.use_gpu)

    def save_weights(self):
        torch.save({
            'policy_state_dict': self.policy.state_dict(),
            'value_state_dict': self.value.state_dict(),
            'cnn_state_dict': self.cnn.state_dict(),
            'ppo_optimizer_state_dict': self.ppo_optimizer.state_dict(),
            'auxppg_optimizer_state_dict': self.aux_ppg_optimizer.state_dict(),
            'ppo_scaler_state_dict': self.ppo_scaler.state_dict(),
            'auxppg_scaler_state_dict': self.auxppg_scaler.state_dict(),
        }, self.folder + '/ppg.tar')
        
    def load_weights(self, device = None):
        if device == None:
            device = self.device

        model_checkpoint = torch.load(self.folder + '/ppg.tar', map_location = device)
        self.policy.load_state_dict(model_checkpoint['policy_state_dict'])        
        self.value.load_state_dict(model_checkpoint['value_state_dict'])
        self.cnn.load_state_dict(model_checkpoint['cnn_state_dict'])
        self.ppo_optimizer.load_state_dict(model_checkpoint['ppo_optimizer_state_dict'])        
        self.aux_ppg_optimizer.load_state_dict(model_checkpoint['auxppg_optimizer_state_dict'])   
        self.ppo_scaler.load_state_dict(model_checkpoint['ppo_scaler_state_dict'])        
        self.auxppg_scaler.load_state_dict(model_checkpoint['auxppg_scaler_state_dict'])  

        if self.is_training_mode:
            self.policy.train()
            self.value.train()
            print('Model is training...')

        else:
            self.policy.eval()
            self.value.eval()
            print('Model is evaluating...')