# -*- coding: utf-8 -*-
"""
Utility functions for linescan endomicroscopy.

@author: Mike Hughes, Applied Optics Group, University of Kent
"""

import numpy as np
import matplotlib.pyplot as plt


"""  calibrate_virtual_slit

Determines the scan parameters (speed, offset and range) for virtual
slit (endo)microscopy. The function takes a 3D numpy array (height, width, image no.)
which contains a stack of images acquired with the scanner fixed at different
voltages. This should produce a strong horizontal line across the image,
providing that the particular voltage results in the line being within the
field-of-view. 

The function checks each image for a prominant line, removing
those that do not have one (this can be adjusted by change the optional parameter 
'threshold').

Using the supplied voltage for each line ('volts', a 1D array) the required scan speed 
(in Volt/s), scan offset (V) and scan range (V) is determined. This requires
the line readout rate of the camera ('lineRate') to be supplied in Hz.
"""
def calibrate_virtual_slit(imStack, volts, lineRate, **kwargs):
    
    prominanceThreshold = kwargs.get('promThreshold', 10)
    brightnessThreshold = kwargs.get('brightThreshold', 2)

    h,w,nImages = np.shape(imStack)
    
    peak = np.zeros((nImages))
    prominance = np.zeros((nImages))
    brightness = np.zeros((nImages))

    # For each image, average horizonally and then detect the peak
    for i in range(nImages):
        
        plot = np.mean(imStack[:,:,i], axis = 1)
    
        peak[i] = np.argmax(plot)
        #print(peak[i])
    
        # peak should be sharp, so have high gradient
        grad = np.abs(np.diff(plot))
        prominance[i] = np.max(grad) / np.mean(grad)
        brightness[i] = np.max(plot) / np.mean(plot)
        #plt.figure()
        #plt.imshow(imStack[:,:,i])
    #print(prominance)
    #print(brightness)
    
    # Select only images where the prominance of the peak is sufficient to
    # mean we must have the laser line visible    
    usePeak = peak[np.logical_and(prominance > prominanceThreshold, brightness > brightnessThreshold)]
    useVolts = volts[np.logical_and(prominance > prominanceThreshold, brightness > brightnessThreshold)]
    #print(usePeak)
    #print(useVolts)      
    # Linear fit allosw requiered scan speed and offset to be determined  
    fit = np.polyfit(usePeak,useVolts,1)
    #plt.figure()
    #plt.plot(useVolts, usePeak)
    speed = lineRate * fit[0]
    offset = fit[1]    
    scanRange = h * fit[0]
    
    return speed, offset, scanRange
    
