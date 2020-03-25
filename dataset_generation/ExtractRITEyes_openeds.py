#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed May 29 16:16:57 2019

@author: rakshit
"""
import os
import cv2
import glob
import copy
import argparse
import matplotlib
import numpy as np
import deepdish as dd
import scipy.io as scio

from PIL import Image
from sklearn.cluster import KMeans
from matplotlib.patches import Ellipse

parser = argparse.ArgumentParser()
parser.add_argument('--noDisp', help='Specify flag to display labelled images', type=int)
parser.add_argument('--path2ds', help='Path to dataset', type=str)
args = parser.parse_args()

from RITEyes_helper.subpixel_python.finalDetector_0 import finalDetector
from RITEyes_helper.helperfunctions import ransac, ElliFit, my_ellipse

if args.noDisp:
    noDisp = True
    print('No graphics')
else:
    noDisp = False
    print('Showing figures')

print('Extracting RITEyes: s-openeds')

gui_env = ['Qt5Agg','WXAgg','TKAgg','GTKAgg']
for gui in gui_env:
    try:
        print("testing: {}".format(gui))
        matplotlib.use(gui,warn=False, force=True)
        from matplotlib import pyplot as plt
        break
    except:
        continue

print("Using: {}".format(matplotlib.get_backend()))
plt.ion()

args.path2ds = '/media/rakshit/tank/Dataset'
PATH_DIR = os.path.join(args.path2ds, 'RITEyes', 'constraint', 's-openeds')
PATH_DS = os.path.join(args.path2ds, 'All')
PATH_MASTER = os.path.join(args.path2ds, 'MasterKey')

Image_counter = 0.0
ds_num = 163

A = np.array([[0,0], [400, 0],[0, 640],[400, 640]])
B = np.array([[-1,-1], [1, -1],[-1, 1],[1, 1]])
H = cv2.findHomography(A, B, method=0)[0]

def mypause(interval):
    backend = plt.rcParams['backend']
    if backend in matplotlib.rcsetup.interactive_bk:
        figManager = matplotlib._pylab_helpers.Gcf.get_active()
        if figManager is not None:
            canvas = figManager.canvas
            if canvas.figure.stale:
                canvas.draw()
            canvas.start_event_loop(interval)
            return

def quantizeMask(wSkin_mask, I):
    # Quantize for pupil and iris.
    # Pupil is red
    # Iris is green
    # Scelra is blue
    r, c, _ = I.shape
    x, y = np.meshgrid(np.arange(0, c), np.arange(0, r))
    mask = np.zeros((r, c))
    mask_red = np.bitwise_and(
            I[:,:,0]>=248, I[:,:,1]==0, I[:,:,2]==0)
    mask_green = np.bitwise_and(
            I[:,:,0]==0, I[:,:,1]>=248, I[:,:,2]==0)
    N_pupil = np.sum(mask_red)
    N_iris = np.sum(mask_green)
    noPupil = False if N_pupil > 20 else True
    noIris = False if N_iris > 20 else True
    # Pupil and Iris regions, absolutely no sclera
    if not noPupil and not noIris:
        initarr = np.array([[0,0,0],
                            [0,0,255],
                            [0,255,0],
                            [255,0,0]])
        feats = I.reshape(-1, 3)
        KM = KMeans(n_clusters=4,
                    max_iter=1000,
                    tol=1e-6, n_init=1,
                    init=initarr).fit(feats)
        mask = KM.predict(feats)
        mask = mask.reshape(r, c)
        loc = (wSkin_mask[:,:,0]<128) & (wSkin_mask[:,:,1]<128) & (wSkin_mask[:,:,2]<128)
        wSkin_mask = copy.deepcopy(mask)
        wSkin_mask[loc] = 0

    if noPupil and not noIris:
        initarr = np.array([[0,0,0],
                            [0,0,255],
                            [0,255,0]])
        feats = I.reshape(-1, 3)
        KM = KMeans(n_clusters=3,
                    max_iter=1000,
                    tol=1e-6, n_init=1,
                    init=initarr).fit(feats)
        mask = KM.predict(feats)
        mask = mask.reshape(r, c)
        loc = (wSkin_mask[:,:,0]<128) & (wSkin_mask[:,:,1]<128) & (wSkin_mask[:,:,2]<128)
        wSkin_mask = copy.deepcopy(mask)
        wSkin_mask[loc] = 0

    if not noPupil and noIris:
        initarr = np.array([[0,0,0],
                            [0,0,255],
                            [255,0,0]])
        feats = I.reshape(-1, 3)
        KM = KMeans(n_clusters=3,
                    max_iter=1000,
                    tol=1e-6, n_init=1,
                    init=initarr).fit(feats)
        mask = KM.predict(feats)
        mask[mask == 2] = 3 # Should actually be 3 for pupil locations
        mask = mask.reshape(r, c)
        loc = (wSkin_mask[:,:,0]<128) & (wSkin_mask[:,:,1]<128) & (wSkin_mask[:,:,2]<128)
        wSkin_mask = copy.deepcopy(mask)
        wSkin_mask[loc] = 0

    if noPupil and noIris:
        initarr = np.array([[0,0,0],
                            [0,0,255]])
        feats = I.reshape(-1, 3)
        KM = KMeans(n_clusters=2,
                    max_iter=1000,
                    tol=1e-6, n_init=1,
                    init=initarr).fit(feats)
        mask = KM.predict(feats)
        mask = mask.reshape(r, c)
        loc = (wSkin_mask[:,:,0]<128) & (wSkin_mask[:,:,1]<128) & (wSkin_mask[:,:,2]<128)
        wSkin_mask = copy.deepcopy(mask)
        wSkin_mask[loc] = 0
    return (wSkin_mask, mask)

list_ds = [ele for ele in os.listdir(PATH_DIR) if os.path.isdir(os.path.join(PATH_DIR, ele))]

for fName in list_ds:
    PATH_IMAGES = os.path.join(PATH_DIR, fName, 'synthetic')
    PATH_MASK_SKIN = os.path.join(PATH_DIR, fName, 'mask-withskin')
    PATH_MASK_NOSKIN = os.path.join(PATH_DIR, fName, 'mask-withoutskin')

    imList = glob.glob(os.path.join(PATH_IMAGES, '*.tif'))

    if not noDisp:
        fig, plts = plt.subplots(1,1)

    # Generate empty dictionaries
    keydict = dict()
    keydict['pupil_loc'] = []
    keydict['archive'] = []
    keydict['data_type'] = 2 #Everything is available
    keydict['resolution'] = []
    keydict['dataset'] = 'RITEyes-C-openeds'
    keydict['subset'] = fName

    # Create an empty dictionary as per agreed structure
    Data = dict()
    Data['Images'] = []
    Data['pupil_loc'] = []
    Data['Masks'] = []
    Data['Masks_noSkin'] = []
    Data['Info'] = []
    Data['Fits'] = {k:[] for k in ['pupil', 'pupil_norm', 'pupil_phi', 'iris', 'iris_norm', 'iris_phi']}
    fr_num = 0

    try:
        for ele in imList:
            imName_withext = os.path.split(ele)[1]
            imName = os.path.splitext(ele)[0]

            path2im = os.path.join(PATH_IMAGES, imName_withext)
            path2mask = os.path.join(PATH_MASK_SKIN, imName_withext)
            path2mask_woskin = os.path.join(PATH_MASK_NOSKIN, imName_withext)

            '''
            I = cv2.imread(path2im, 0)
            maskIm = cv2.imread(path2mask)[:,:,[2,1,0]]
            maskIm_woskin = cv2.imread(path2mask_woskin)[:,:,[2,1,0]]
            '''
            I = np.asarray(Image.open(path2im).convert('L'))
            maskIm = np.asarray(Image.open(path2mask).convert('RGB'))
            maskIm_woskin = np.asarray(Image.open(path2mask_woskin).convert('RGB'))
            maskIm, maskIm_woskin = quantizeMask(maskIm, maskIm_woskin)

            Data['Images'].append(I)
            Data['Masks'].append(maskIm)
            Data['Masks_noSkin'].append(maskIm_woskin)
            Data['Info'].append(imName)
            keydict['resolution'].append(I.shape)
            keydict['archive'].append(ds_num)

            pEdges = finalDetector(maskIm_woskin.astype(np.double),
                                   thres=0.1,
                                   order=2,
                                   mode=0)
            loc_pupil = ((pEdges['i0'] == 2) & (pEdges['i1'] == 3)) | \
                        ((pEdges['i0'] == 3) & (pEdges['i1'] == 2))
            loc_iris = ((pEdges['i0'] == 1) & (pEdges['i1'] == 2)) | \
                        ((pEdges['i0'] == 2) & (pEdges['i1'] == 1))

            # Pupil ellipse fit
            temp_pts = np.stack([pEdges['x'][loc_pupil], pEdges['y'][loc_pupil]], axis=1) # Improve readability
            model_pupil = ransac(temp_pts, ElliFit, 15, 10, 0.05, np.round(temp_pts.shape[0]/2)).loop()
            pupil_fit_error = my_ellipse(model_pupil.model).verify(temp_pts)

            pupil_loc = model_pupil.model[:2]

            # Iris ellipse fit
            temp_pts = np.stack([pEdges['x'][loc_iris], pEdges['y'][loc_iris]], axis=1)
            model_iris = ransac(temp_pts, ElliFit, 15, 10, 0.05, np.round(temp_pts.shape[0]/2)).loop()
            iris_fit_error = my_ellipse(model_iris.model).verify(temp_pts)

            model_pupil_norm = my_ellipse(model_pupil.model).transform(H)[0][:-1] if pupil_fit_error <= 0.1 else np.array([-1, -1, -1, -1, -1])
            model_pupil.Phi = model_pupil.Phi if pupil_fit_error <= 0.1 else np.array([-1, -1, -1, -1, -1])
            model_iris_norm = my_ellipse(model_iris.model).transform(H)[0][:-1] if iris_fit_error <= 0.1 else np.array([-1, -1, -1, -1, -1])
            model_iris.Phi = model_iris.Phi if iris_fit_error <= 0.1 else np.array([-1, -1, -1, -1, -1])

            Data['Fits']['pupil'].append(model_pupil.model)
            Data['Fits']['pupil_norm'].append(model_pupil_norm)
            Data['Fits']['pupil_phi'].append(model_pupil.Phi)
            Data['Fits']['iris'].append(model_iris.model)
            Data['Fits']['iris_norm'].append(model_iris_norm)
            Data['Fits']['iris_phi'].append(model_iris.Phi)

            keydict['pupil_loc'].append(pupil_loc)
            Data['pupil_loc'].append(pupil_loc)

            fr_num += 1
            if not noDisp:
                if fr_num == 1:
                    cE = Ellipse(tuple(pupil_loc),
                                 2*model_pupil.model[2],
                                 2*model_pupil.model[3],
                                 angle=np.rad2deg(model_pupil.model[-1]))
                    cL = Ellipse(tuple(model_iris.model[0:2]),
                                       2*model_iris.model[2],
                                       2*model_iris.model[3],
                                       np.rad2deg(model_iris.model[4]))
                    cE.set_facecolor('None')
                    cE.set_edgecolor((1.0, 0.0, 0.0))
                    cL.set_facecolor('None')
                    cL.set_edgecolor((0.0, 1.0, 0.0))
                    cI = plts.imshow(I)
                    cM = plts.imshow(maskIm, alpha=0.5)
                    cX = plts.scatter(pupil_loc[0], pupil_loc[1])
                    plts.add_patch(cE)
                    plts.add_patch(cL)
                    plt.show()
                    plt.pause(.01)
                else:
                    cE.center = tuple(pupil_loc)
                    cE.angle = np.rad2deg(model_pupil.model[-1])
                    cE.width = 2*model_pupil.model[2]
                    cE.height = 2*model_pupil.model[3]
                    cL.center = tuple(model_iris.model[0:2])
                    cL.width = 2*model_iris.model[2]
                    cL.height = 2*model_iris.model[3]
                    cL.angle = np.rad2deg(model_iris.model[-1])
                    newLoc = np.array([pupil_loc[0], pupil_loc[1]])
                    cI.set_data(I)
                    cM.set_data(maskIm)
                    cX.set_offsets(newLoc)
                    mypause(0.01)

        keydict['resolution'] = np.stack(keydict['resolution'], axis=0)
        keydict['archive'] = np.stack(keydict['archive'], axis=0)
        keydict['pupil_loc'] = np.stack(keydict['pupil_loc'], axis=0)
        Data['pupil_loc'] = np.stack(Data['pupil_loc'], axis=0)
        Data['Images'] = np.stack(Data['Images'], axis=0)
        Data['Masks'] = np.stack(Data['Masks'], axis=0)
        Data['Masks_noSkin'] = np.stack(Data['Masks_noSkin'], axis=0)
        Data['Fits']['pupil'] = np.stack(Data['Fits']['pupil'], axis=0)
        Data['Fits']['pupil_norm'] = np.stack(Data['Fits']['pupil_norm'], axis=0)
        Data['Fits']['iris'] = np.stack(Data['Fits']['iris'], axis=0)
        Data['Fits']['iris_norm'] = np.stack(Data['Fits']['iris_norm'], axis=0)
        Data['Fits']['pupil_phi'] = np.stack(Data['Fits']['pupil_phi'], axis=0)
        Data['Fits']['iris_phi'] = np.stack(Data['Fits']['iris_phi'], axis=0)

        # Save data
        dd.io.save(os.path.join(PATH_DS, str(ds_num)+'.h5'), Data)
        scio.savemat(os.path.join(PATH_MASTER, str(ds_num)), keydict, appendmat=True)
        ds_num=ds_num+1
    except:
        print('Data not present for {}'.format(fName))
        continue