import torch

class QLoss():
    def __init__(self, gamma = 0.99):
        self.gamma = gamma

    def compute_loss(self, predicted_q_value1, naive_predicted_q_value1, predicted_q_value2, naive_predicted_q_value2, target_next_q1, target_next_q2, reward, done):
        naive_predicted_q_value = torch.min(naive_predicted_q_value1, naive_predicted_q_value2)
        predicted_q_value       = torch.min(predicted_q_value1, predicted_q_value2)
        cql_regularizer         = (naive_predicted_q_value - predicted_q_value).mean()

        next_value              = torch.min(target_next_q1, target_next_q2).detach()
        target_q_value          = (reward + (1 - done) * self.gamma * next_value).detach()

        td_error1               = ((target_q_value - predicted_q_value1).pow(2) * 0.5).mean()
        td_error2               = ((target_q_value - predicted_q_value2).pow(2) * 0.5).mean()

        return td_error1 + td_error2 + cql_regularizer