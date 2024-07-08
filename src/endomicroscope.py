# -*- coding: utf-8 -*-
"""
Endomicroscope GUI

A GUI for fibre bundle endomicroscopy probes, including widefield and
virtual slit linescan systems.

@author: Mike Hughes, Applied Optics Group, University of Kent

"""

import sys 
import os
sys.path.append('..\\..\\cas\\src')
os.environ['KMP_DUPLICATE_LIB_OK']='True'
sys.path.append('..\\..\\pyfibrebundle\\src')

import time
import numpy as np
import math
import pickle
import threading

import matplotlib.pyplot as plt
from PIL import Image
import cv2 as cv
import logging

from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QPalette, QColor, QImage, QPixmap, QPainter, QPen, QGuiApplication, QIcon
from PyQt5.QtGui import QPainter, QBrush, QPen

try:
    import nidaqmx
    from nidaqmx import stream_writers
except:
    pass    

import pybundle
from pybundle import PyBundle
from pybundle import SuperRes

from cas_gui.subclasses.cas_bundle import CAS_GUI_Bundle
from cas_gui.threads.bundle_processor import BundleProcessor

import linescan_utilities


class Endomicroscope(CAS_GUI_Bundle):
    
    authorName = "AOG"
    appName = "Endomicroscope"
    windowTitle = "Kent Endomicroscope"
    resPath = "../../cas/res"
    
    # If Simulated Camera is chosen, this is the source file:
    #sourceFilename = r"C:\Users\AOG\OneDrive - University of Kent\Experimental\Endomicroscopy\Example Videos\leaf widefield\leaf.tif"
    sourceFilename = r"C:\Users\mrh40\Dropbox\Programming\Python\endomicroscope\dev\data\record_2024_06_07_15_04_29.tif"
    rawImageBufferSize = 10
    imageDisplaySize = 300
    controlPanelSize = 250
    mosaicingEnabled = False
    manualImageTransfer = False
    
    # Set True for Virtual Slit LineScan
    ls = False             
        
    # DAQ fo virtual slit linescan
    lsAOChannel= "Dev1/ao0"
    lsCtrChannel = "Dev1/ctr0"
        
    # Virtual slit linescan calibration values
    lsCalibMinV = 0
    lsCalibMaxV = 3
    lsCalibStepV = 0.2
    lsCalibExposure = 8000
    lsCalibGain = 18
    lsOffsetTweak = -0.03
    lineRate = 130750.6
    
    
    def __init__(self,parent=None):
     
        super(Endomicroscope, self).__init__(parent)    
        
        try:
            self.load_calibration()
        except:
            pass
        
        
    
    def create_layout(self):
        """ Creates the GUI by creating widgets or calling functions which
        create widgets.
        """        
          
        super().create_layout()
        
                
        if self.ls is True:
            
            # Create the additional menu buttons needed for HoloBundle
            self.lsMenuButton = self.create_menu_button("Scanning", QIcon('../res/grid_white.svg'), self.ls_menu_button_clicked, True, True, 8)
        
            # Create the additional menu panels needed for line scanning
            self.lsPanel = self.create_ls_panel()
       
              
        self.mainDisplay.set_auto_scale(True)
        self.mainDisplay.minAutoscaleUpper = 20
        
        
    # Control options for virtual slit linescan
    def create_ls_panel(self):
        
        widget, layout = self.panel_helper(title = "Line Scanning")
        
        self.lsCalibBtn=QPushButton('Auto Calibration')
        self.lsScanSpeedInput = QDoubleSpinBox(objectName = 'lsScanSpeedInput')
        self.lsScanOffsetInput = QDoubleSpinBox(objectName = 'lsScanOffsetInput')
        self.lsScanRangeInput = QDoubleSpinBox(objectName = 'lsScanRangeInput')
        
        self.lsScanSpeedInput.setMaximum(1000)
        self.lsScanSpeedInput.setMinimum(-1000)
        
        self.lsScanOffsetInput.setMaximum(5)
        self.lsScanOffsetInput.setMinimum(-5)
        
        self.lsScanRangeInput.setMaximum(5)
        self.lsScanRangeInput.setMinimum(-5 )  
        
        self.lsScanOffsetInput.setSingleStep(0.001)
        self.lsScanOffsetInput.setDecimals(3)

        self.lsScanSpeedInput.setSingleStep(0.1)
        self.lsScanSpeedInput.setDecimals(1)
        
        self.lsDualCheck = QCheckBox("Enhanced Mode", objectName="ldDualCheck")
       
        self.lsDualOffsetInput = QDoubleSpinBox(objectName = 'lsDualOffsetInput')
        self.lsDualOffsetInput.setMaximum(1)
        self.lsDualOffsetInput.setMinimum(-1)  
        
        self.lsFixedCheck = QCheckBox("Scan Hold", objectName = "lsFixedCheck")

        self.lsFixedVoltageInput = QDoubleSpinBox(objectName = "lsFixedVoltageInput")
        self.lsFixedVoltageInput.setMinimum(-10)
        self.lsFixedVoltageInput.setMaximum(10)
        
        layout.addWidget(self.lsCalibBtn)
        layout.addWidget(QLabel("Scan Speed (V/s):"))
        layout.addWidget(self.lsScanSpeedInput)
        layout.addWidget(QLabel("Scan Offset (V):"))
        layout.addWidget(self.lsScanOffsetInput)
        layout.addWidget(QLabel("Scan Range (V):"))
        layout.addWidget(self.lsScanRangeInput)
        layout.addWidget(self.lsFixedCheck)
        layout.addWidget(QLabel("Scan Hold Position (V):"))
        layout.addWidget(self.lsFixedVoltageInput )
        layout.addWidget(self.lsDualCheck)
        layout.addWidget(QLabel("Enhanced Offset (V):"))
        layout.addWidget(self.lsDualOffsetInput)

        self.lsScanSpeedInput.valueChanged[float].connect(self.scanning_parameters_changed)
        self.lsScanOffsetInput.valueChanged[float].connect(self.scanning_parameters_changed)
        self.lsScanRangeInput.valueChanged[float].connect(self.scanning_parameters_changed)
        self.lsCalibBtn.clicked.connect(self.calibrate_ls)

        self.lsFixedCheck.stateChanged.connect(self.scanning_parameters_changed)
        self.lsFixedVoltageInput.valueChanged[float].connect(self.scanning_parameters_changed)
        
        self.lsDualCheck.stateChanged.connect(self.scanning_parameters_changed)
        self.lsDualOffsetInput.valueChanged[float].connect(self.scanning_parameters_changed)
        
        return widget
    
    
    def ls_menu_button_clicked(self):
        self.expanding_menu_clicked(self.lsMenuButton, self.lsPanel)
            
    
    def scanning_parameters_changed(self, event):
        """ Called when any options on the linescan control panel are changed"""
        self.init_ls_scanning()
        

    def init_ls_scanning(self):
        """ For virtual slit linescan, sets up DAQ to generate ramp voltage on 
        galvos, triggered by strobe from camera
        """
        
        lineRate = 130750.6      # Camera line rate parameter
        if self.imageProcessor is not None:
            self.imageProcessor.dualMode = self.lsDualCheck.isChecked()
        
        if self.camOpen is True:
            # Stop tasks
            try:                
                self.aoTask.close()
                self.ctrTask.close()
                self.aoTask.stop()
                self.ctrTask.stop()
                self.aoTask.clear()
                self.ctrTask.clear()
            except:
                print("Could not dispose of old task.")
            
            # lsFixedCheck is an option for the user to fix a voltage
            # rather than scanning, for debug purposes
            if self.lsFixedCheck.isChecked() is False:  
     
                self.sampleRate = 250000   # Max rate of DAQ
                offset = self.lsScanOffsetInput.value()
                scanSpeed = self.lsScanSpeedInput.value()
                scanRange = self.lsScanRangeInput.value()    
                
                if scanSpeed > 0:
                    nPoints = np.abs(int(scanRange / scanSpeed * self.sampleRate))
                else:
                    nPoints = 1
                print(nPoints)    
                vals = np.linspace(offset, offset + scanRange, nPoints)
        
                #self.lsDualOffset = 0.01
                #self.lsDualMode = False
                if self.lsDualCheck.isChecked():
                    offsetVals = vals + self.lsDualOffsetInput.value()
                    vals = np.concatenate((vals, offsetVals))
                
                self.aoTask = nidaqmx.Task()
                self.ctrTask = nidaqmx.Task() 
              
                self.aoTask.ao_channels.add_ao_voltage_chan("dev1/ao0")

                        
                # Create a counter task that will be triggered by PFI0
                self.ctrTask.co_channels.add_co_pulse_chan_freq("dev1/ctr0", freq = self.sampleRate)
                self.ctrTask.timing.cfg_implicit_timing(samps_per_chan = nPoints)
                self.ctrTask.triggers.start_trigger.cfg_dig_edge_start_trig("/dev1/PFI0", trigger_edge = nidaqmx.constants.Edge.FALLING)
                self.ctrTask.triggers.start_trigger.retriggerable = True
                
                # Set the AO clock source to be the counter clock output so that it will be triggered by PFI0
                self.aoTask.timing.cfg_samp_clk_timing(self.sampleRate, sample_mode = nidaqmx.constants.AcquisitionType.CONTINUOUS, samps_per_chan = nPoints, source = "/dev1/Ctr0InternalOutput")
                #self.aoTask.timing.cfg_samp_clk_timing(self.sampleRate, sample_mode = nidaqmx.constants.AcquisitionType.CONTINUOUS, source = "/Dev1/Ctr0InternalOutput")
                
              
                writer = nidaqmx.stream_writers.AnalogSingleChannelWriter(self.aoTask.out_stream)
                
                # Send voltage values
                writer.write_many_sample(vals)
              
                self.aoTask.start()
                self.ctrTask.start()
                # Make sure to start aotask first in case it misses some points
                 
                
               # except:
                #    QMessageBox.about(self, "Error", "Unable to connect to scanner.")
            
            else:
                self.ls_fixed_voltage(self.lsFixedVoltageInput.value())




    def stop_ls(self):
        """ Stops the galvo scanner"""
        try:
            self.aoTask.close()
        except:
            print("Could not close DAQ AO")
        
        try: 
            self.ctrTask.close()
        except:
            print("Could not close DAQ Counter")

        
    def start_acquire(self):
        """ In addition to the super class acquisition, also starts the galvo
        scanner if we are doing line scanning
        """
        super().start_acquire()
        if self.ls is True:
            self.init_ls_scanning()
        
    
    def end_acquire(self):
        """ In addition to the super class stop acquisition, also stops the galvo
        scanner if we are doing line scanning
        """
        if self.ls is True:
            self.stop_ls()
        super().end_acquire()
        
        
    def global_calibrate(self):
        """ Acquires a background image and then call the calibrate function
        of pyfibrebundle.
        """
        self.acquire_background()
        self.handle_calibrate()
        
        
   
    def calibrate_ls(self, event):
        """ Determines the galvo scanning speed and offset so that the scanning
        line is aligned with the camera rolling shutter """
        
        
        # Grab a series of images at different galvo voltages
        testV = np.arange(self.lsCalibMinV, self.lsCalibMaxV, self.lsCalibStepV)
        testIm = self.get_single_image(exposure = self.lsCalibExposure, gain = self.lsCalibGain)

        im = np.zeros((np.shape(self.currentImage)[0], np.shape(self.currentImage)[1],np.shape(testV)[0] ))
        for i, v in enumerate(testV):
            self.ls_fixed_voltage(v)
            time.sleep(0.1)
            im[:,:, i] = self.get_single_image(exposure = self.lsCalibExposure, gain = self.lsCalibGain)

        speed, offset, scanRange = linescan_utilities.calibrate_virtual_slit(im, testV, self.lineRate)
        
        self.lsScanSpeedInput.setValue(-speed)
        self.lsScanOffsetInput.setValue(offset + self.lsOffsetTweak)
        self.lsScanRangeInput.setValue(scanRange)

        self.init_ls_scanning()
        self.update_camera_from_GUI()
        
    
    def get_single_image(self, **kwargs):
        """ Grab a single image, optionally with exposure and gain set. Note this will
        flush the acquisition buffer
        """        
        exposure = kwargs.get('exposure', None)
        gain = kwargs.get('gain', None)
        if exposure is not None:
            self.imageThread.cam.set_exposure(exposure)
        if gain is not None:
            self.imageThread.cam.set_gain(gain)
    
        self.imageThread.flush_buffer()
        
        return self.imageThread.get_next_image_wait()
     
    
    def ls_fixed_voltage(self,volts):
        """ Write a fixed voltage to the scanner and leave it there"""
        
        try:
            self.stop_ls()  # stops the current scanning
        except:
            pass
        self.aoTask = nidaqmx.Task()
        self.aoTask.ao_channels.add_ao_voltage_chan(self.lsAOChannel)
        self.aoTask.write(volts)
        
                 

if __name__ == '__main__':    
    app=QApplication(sys.argv)
  
       
    window=Endomicroscope()
    window.show()
    sys.exit(app.exec_())

