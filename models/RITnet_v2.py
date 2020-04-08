#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@author: rakshit
"""
import torch
import numpy as np
import torch.nn as nn
import torch.nn.functional as F

from pytorchtools import linStack
from utils import normPts, conf_Loss
from loss import get_ptLoss, get_segLoss, get_seg2ptLoss

def getSizes(chz, growth, blks=4):
    # This function does not calculate the size requirements for head and tail

    # Encoder sizes
    sizes = {'enc': {'inter':[], 'ip':[], 'op': []},
             'dec': {'skip':[], 'ip': [], 'op': []}}
    sizes['enc']['inter'] = np.array([chz*(i+1) for i in range(0, blks)])
    sizes['enc']['op'] = np.array([np.int(growth*chz*(i+1)) for i in range(0, blks)])
    sizes['enc']['ip'] = np.array([chz] + [np.int(growth*chz*(i+1)) for i in range(0, blks-1)])

    # Decoder sizes
    sizes['dec']['skip'] = sizes['enc']['ip'][::-1] + sizes['enc']['inter'][::-1]
    sizes['dec']['ip'] = sizes['enc']['op'][::-1] #+ sizes['dec']['skip']
    sizes['dec']['op'] = np.append(sizes['enc']['op'][::-1][1:], chz)
    return sizes

class Transition_down(nn.Module):
    def __init__(self, in_c, out_c, down_size, norm, actfunc):
        super(Transition_down, self).__init__()
        self.conv = nn.Conv2d(in_c, out_c, kernel_size=1, padding=0)
        self.max_pool = nn.AvgPool2d(kernel_size=down_size) if down_size else False
        self.norm = norm(num_features=in_c)
        self.actfunc = actfunc
    def forward(self, x):
        x = self.actfunc(self.norm(x))
        x = self.conv(x)
        x = self.max_pool(x) if self.max_pool else x
        return x

class DenseNet2D_down_block(nn.Module):
    def __init__(self, in_c, inter_c, op_c, down_size, norm, actfunc):
        super(DenseNet2D_down_block, self).__init__()
        self.conv1 = nn.Conv2d(in_c, inter_c, kernel_size=3, padding=1)
        self.conv21 = nn.Conv2d(in_c+inter_c, inter_c, kernel_size=1, padding=0)
        self.conv22 = nn.Conv2d(inter_c, inter_c, kernel_size=3, padding=1)
        self.conv31 = nn.Conv2d(in_c+2*inter_c, inter_c, kernel_size=1, padding=0)
        self.conv32 = nn.Conv2d(inter_c, inter_c, kernel_size=3, padding=1)
        self.actfunc = actfunc
        self.bn = norm(num_features=in_c)
        self.TD = Transition_down(inter_c+in_c, op_c, down_size, norm, actfunc)

    def forward(self, x):
        x1 = self.actfunc(self.conv1(self.bn(x)))
        x21 = torch.cat([x, x1], dim=1)
        x22 = self.actfunc(self.conv22(self.conv21(x21)))
        x31 = torch.cat([x21, x22], dim=1)
        out = self.actfunc(self.conv32(self.conv31(x31)))
        out = torch.cat([out, x], dim=1)
        return out, self.TD(out)

class DenseNet2D_up_block(nn.Module):
    def __init__(self, skip_c, in_c, out_c, up_stride, actfunc):
        super(DenseNet2D_up_block, self).__init__()
        self.conv11 = nn.Conv2d(skip_c+in_c, out_c, kernel_size=1, padding=0)
        self.conv12 = nn.Conv2d(out_c, out_c, kernel_size=3, padding=1)
        self.conv21 = nn.Conv2d(skip_c+in_c+out_c, out_c, kernel_size=1,padding=0)
        self.conv22 = nn.Conv2d(out_c, out_c, kernel_size=3, padding=1)
        self.actfunc = actfunc
        self.up_stride = up_stride

    def forward(self, prev_feature_map, x):
        x = F.interpolate(x,
                          mode='bilinear',
                          align_corners=False,
                          scale_factor=self.up_stride)
        x = torch.cat([x, prev_feature_map], dim=1)
        x1 = self.actfunc(self.conv12(self.conv11(x)))
        x21 = torch.cat([x, x1],dim=1)
        out = self.actfunc(self.conv22(self.conv21(x21)))
        return out

class convBlock(nn.Module):
    def __init__(self, in_c, inter_c, out_c, actfunc):
        super(convBlock, self).__init__()
        self.conv1 = nn.Conv2d(in_c, inter_c, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(inter_c, inter_c, kernel_size=3, padding=1)
        self.conv3 = nn.Conv2d(inter_c, out_c, kernel_size=3, padding=1)
        self.actfunc = actfunc
    def forward(self, x):
        x = self.conv1(x)
        x = self.conv2(x) # Remove x if not working properly
        x = self.conv3(x)
        x = self.actfunc(x)
        return x

class DenseNet_encoder(nn.Module):
    def __init__(self, in_c=1, chz=32, actfunc=F.leaky_relu, growth=1.5, norm=nn.BatchNorm2d):
        super(DenseNet_encoder, self).__init__()
        sizes = getSizes(chz, growth)
        interSize = sizes['enc']['inter']
        opSize = sizes['enc']['op']
        ipSize = sizes['enc']['ip']

        self.head = convBlock(in_c=1,
                                inter_c=chz,
                                out_c=chz,
                                actfunc=actfunc)
        self.down_block1 = DenseNet2D_down_block(in_c=ipSize[0],
                                                 inter_c=interSize[0],
                                                 op_c=opSize[0],
                                                 down_size=2,
                                                 norm=norm,
                                                 actfunc=actfunc)
        self.down_block2 = DenseNet2D_down_block(in_c=ipSize[1],
                                                 inter_c=interSize[1],
                                                 op_c=opSize[1],
                                                 down_size=2,
                                                 norm=norm,
                                                 actfunc=actfunc)
        self.down_block3 = DenseNet2D_down_block(in_c=ipSize[2],
                                                 inter_c=interSize[2],
                                                 op_c=opSize[2],
                                                 down_size=2,
                                                 norm=norm,
                                                 actfunc=actfunc)
        self.down_block4 = DenseNet2D_down_block(in_c=ipSize[3],
                                                 inter_c=interSize[3],
                                                 op_c=opSize[3],
                                                 down_size=2,
                                                 norm=norm,
                                                 actfunc=actfunc)
    def forward(self, x):
        x = self.head(x) # chz
        skip_1, x = self.down_block1(x) # chz
        skip_2, x = self.down_block2(x) # 2 chz
        skip_3, x = self.down_block3(x) # 4 chz
        skip_4, x = self.down_block4(x) # 8 chz
        return skip_4, skip_3, skip_2, skip_1, x

class DenseNet_decoder(nn.Module):
    def __init__(self, chz, out_c, growth, actfunc=F.leaky_relu, norm=nn.BatchNorm2d):
        super(DenseNet_decoder, self).__init__()
        sizes = getSizes(chz, growth)
        skipSize = sizes['dec']['skip']
        opSize = sizes['dec']['op']
        ipSize = sizes['dec']['ip']

        self.up_block4 = DenseNet2D_up_block(skipSize[0], ipSize[0], opSize[0], 2, actfunc)
        self.up_block3 = DenseNet2D_up_block(skipSize[1], ipSize[1], opSize[1], 2, actfunc)
        self.up_block2 = DenseNet2D_up_block(skipSize[2], ipSize[2], opSize[2], 2, actfunc)
        self.up_block1 = DenseNet2D_up_block(skipSize[3], ipSize[3], opSize[3], 2, actfunc)

        self.final = convBlock(chz, chz, out_c, actfunc)

    def forward(self, skip4, skip3, skip2, skip1, x):
         x = self.up_block4(skip4, x)
         x = self.up_block3(skip3, x)
         x = self.up_block2(skip2, x)
         x = self.up_block1(skip1, x)
         o = self.final(x)
         return o

class DenseNet2D(nn.Module):
    def __init__(self,
                 chz=32,
                 growth=1.2,
                 actfunc=F.leaky_relu,
                 norm=nn.InstanceNorm2d,
                 selfCorr=False,
                 disentangle=False):
        super(DenseNet2D, self).__init__()

        self.sizes = getSizes(chz, growth)

        self.toggle = True
        self.selfCorr = selfCorr
        self.disentangle = disentangle
        self.disentangle_alpha = 10

        self.enc = DenseNet_encoder(in_c=1, chz=chz, actfunc=actfunc, growth=growth, norm=norm)
        self.dec = DenseNet_decoder(chz=chz, out_c=3, actfunc=actfunc, growth=growth, norm=norm)
        self.bottleneck_lin = linStack(num_layers=2,
                                           in_dim=self.sizes['enc']['op'][-1],
                                           hidden_dim=64,
                                           out_dim=2,
                                           bias=True,
                                           actBool=True,
                                           dp=0.0)
        self._initialize_weights()

    def setDatasetInfo(self, numSets=2):
        # Produces a 1 layered MLP which directly maps
        self.numSets = numSets
        self.dsIdentify_lin = linStack(num_layers=2,
                                       in_dim=self.sizes['enc']['op'][-1],
                                       hidden_dim=64,
                                       out_dim=numSets,
                                       bias=True,
                                       actBool=False,
                                       dp=0.0)

    def forward(self, x, target, pupil_center, spatWts, distMap, cond, ID, alpha):
        '''
        ID: A Tensor containing information about the dataset or subset a entry
        belongs to.
        '''
        x4, x3, x2, x1, x = self.enc(x)
        latent = torch.mean(x.flatten(start_dim=2), -1) # [B, features]
        pred_c = self.bottleneck_lin(latent)
        op = self.dec(x4, x3, x2, x1, x)

        # Compute seg losses
        l_seg = get_segLoss(op, target, spatWts, distMap, cond, alpha)
        l_pt = get_ptLoss(pred_c, normPts(pupil_center, target.shape[1:]), cond)
        l_seg2pt, pred_c_seg = get_seg2ptLoss(op[:, 2, ...],
                                              normPts(pupil_center,
                                                      target.shape[1:]), 1, cond)

        if self.disentangle:
            pred_ds = self.dsIdentify_lin(latent)
            # Disentanglement procedure
            if self.toggle:
                # Primary loss + alpha*confusion
                if self.selfCorr:
                    loss = 10*l_seg+l_pt+l_seg2pt+F.l1_loss(pred_c_seg, pred_c)
                else:
                    loss = 10*l_seg+l_pt+l_seg2pt
                loss += self.disentangle_alpha*conf_Loss(pred_ds,
                                                         ID.to(torch.long),
                                                         self.toggle)
            else:
                # Secondary loss
                loss = conf_Loss(pred_ds, ID.to(torch.long), self.toggle)
        else:
            # No disentanglement, proceed regularly
            if self.selfCorr:
                loss = 10*l_seg+l_pt+l_seg2pt+F.l1_loss(pred_c_seg, pred_c)
            else:
                loss = 10*l_seg+l_pt+l_seg2pt
        return op, latent, pred_c, pred_c_seg, loss.unsqueeze(0)

    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                n = m.kernel_size[0] * m.kernel_size[1] * m.out_channels
                m.weight.data.normal_(0, np.sqrt(2. / n))
                if m.bias is not None:
                    m.bias.data.zero_()
            elif isinstance(m, nn.BatchNorm2d):
                m.weight.data.fill_(1)
                m.bias.data.zero_()
            elif isinstance(m, nn.Linear):
                n = m.weight.size(1)
                m.weight.data.normal_(0, 0.01)
                m.bias.data.zero_()