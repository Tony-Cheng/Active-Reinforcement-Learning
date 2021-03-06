from collections import namedtuple
import random
import torch
import cv2

class ReplayMemory(object):
    def __init__(self, capacity, state_shape, n_actions, device):
        c, h, w = state_shape
        self.capacity = capacity
        self.device = device
        self.m_states = torch.zeros((capacity, c, h, w), dtype=torch.uint8)
        self.m_actions = torch.zeros((capacity, 1), dtype=torch.long)
        self.m_rewards = torch.zeros((capacity, 1), dtype=torch.int8)
        self.m_dones = torch.zeros((capacity, 1), dtype=torch.bool)
        self.position = 0
        self.size = 0

    def push(self, state, action, reward, done):
        """Saves a transition."""
        self.m_states[self.position] = state  # 5,84,84
        self.m_actions[self.position, 0] = action
        self.m_rewards[self.position, 0] = reward
        self.m_dones[self.position, 0] = done
        self.position = (self.position + 1) % self.capacity
        self.size = max(self.size, self.position)

    def sample(self, bs):
        i = torch.randint(0, high=self.size, size=(bs,))
        bs = self.m_states[i, :32].to(self.device)
        bns = self.m_states[i, 8:].to(self.device)
        ba = self.m_actions[i].to(self.device)
        br = self.m_rewards[i].to(self.device).float()
        bd = self.m_dones[i].to(self.device).float()
        return bs, ba, br, bns, bd

    def __len__(self):
        return self.size

class RankedReplayMemory(object):
    def __init__(self, capacity, state_shape, n_actions, rank_func, AMN_net, replacement=False, device='cuda'):
        c, h, w = state_shape
        self.capacity = capacity
        self.device = device
        self.m_states = torch.zeros((capacity, c, h, w), dtype=torch.uint8)
        self.m_actions = torch.zeros((capacity, 1), dtype=torch.long)
        self.m_rewards = torch.zeros((capacity, 1), dtype=torch.int8)
        self.m_dones = torch.zeros((capacity, 1), dtype=torch.bool)
        self.position = 0
        self.size = 0
        self.rank_func = rank_func
        self.AMN_net = AMN_net
        self.replacement = replacement

    def push(self, state, action, reward, done):
        """Saves a transition."""
        self.m_states[self.position] = state  # 5,84,84
        self.m_actions[self.position, 0] = action
        self.m_rewards[self.position, 0] = reward
        self.m_dones[self.position, 0] = done
        self.position = (self.position + 1) % self.capacity
        self.size = max(self.size, self.position)

    def sample(self, percentage=0.1):
        _, i = torch.sort(self.rank_func(
            self.AMN_net, self.m_states[: self.size, :32], device=self.device), descending=True)
        i = i[: int(percentage * self.size)]
        i = i[torch.randperm(i.shape[0])]
        # i = torch.randint(0, high=self.size, size=(bs,))
        bs = self.m_states[i, :32]
        bns = self.m_states[i, 8:]
        ba = self.m_actions[i]
        br = self.m_rewards[i].float()
        bd = self.m_dones[i].float()
        return bs, ba, br, bns, bd

    def __len__(self):
        return self.size