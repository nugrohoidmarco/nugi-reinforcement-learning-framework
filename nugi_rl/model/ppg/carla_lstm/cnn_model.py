import torch.nn as nn

from model.components.ASPP import AtrousSpatialPyramidConv2d
from model.components.SeperableConv2d import DepthwiseSeparableConv2d
from model.components.Downsampler import Downsampler

class ExtractEncoder(nn.Module):
    def __init__(self, dim):
        super(ExtractEncoder, self).__init__()

        self.conv1 = nn.Sequential(
            DepthwiseSeparableConv2d(dim, dim, kernel_size = 3, stride = 1, padding = 1, bias = False),
            nn.ReLU(),
            DepthwiseSeparableConv2d(dim, dim, kernel_size = 3, stride = 1, padding = 1, bias = False),
        )

    def forward(self, x):
        x1 = self.conv1(x)
        x1 = x + x1

        return x1

class CnnModel(nn.Module):
    def __init__(self):
      super(CnnModel, self).__init__()   

      self.conv = nn.Sequential(
        AtrousSpatialPyramidConv2d(3, 8),
        DepthwiseSeparableConv2d(8, 8, kernel_size = 3, stride = 1, padding = 1),
        nn.ReLU(),
        Downsampler(8, 16),
        ExtractEncoder(16),
        Downsampler(16, 32),
        ExtractEncoder(32),
        Downsampler(32, 64),
        ExtractEncoder(64),
        DepthwiseSeparableConv2d(64, 128, kernel_size = 5, stride = 1, padding = 0),
        nn.ReLU(),
      )
        
    def forward(self, image, detach = False):
      n, t = image.shape[0], 0

      if len(image.shape) == 5:
        n, t, c, h, w = image.shape
        image = image.transpose(0, 1).reshape(n * t, c, h, w)

      out = self.conv(image)
      out = out.mean([-1, -2])

      if t > 0:
        out = out.view(t, n, -1)

      if detach:
        return out.detach()
      else:
        return out