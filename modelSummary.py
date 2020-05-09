#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar  2 12:32:15 2020

@author: rakshit
"""

from models.RITnet_v1 import DenseNet2D as DN_v1
from models.RITnet_v2 import DenseNet2D as DN_v2
from models.RITnet_v3 import DenseNet2D as DN_v3
from models.deepvog_pytorch import DeepVOG_pytorch

model_dict = {}
model_dict['ritnet_v1'] = DN_v1()
model_dict['ritnet_v2'] = DN_v2() # Iris and Pupil scheme does not work well
model_dict['ritnet_v3'] = DN_v3()
model_dict['deepvog'] = DeepVOG_pytorch()
