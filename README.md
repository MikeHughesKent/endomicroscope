# Endomicroscope GUI

Endomicroscope GUI is a graphical user interface for fibre bundle endomicroscopic microscopes in Python.

It is an extension of CAS-bundle which is itself an extension of [Kent CAS](https://www.github.com/mikehugheskent/cas), the Kent Camera Acquisition System. 

It also uses the [pyfibrebundle package](https://www.github.com/mikehugheskent/pyfibrebundle) for real-time processing of the fibre bundle images.

Endomicroscope and CAS-GUI are developed in 
[Mike Hughes' lab](https://research.kent.ac.uk/applied-optics/hughes) 
in the [Applied Optics Group](https://research.kent.ac.uk/applied-optics/), 
School of Physics & Astronomy, University of Kent.

We use endomicrscope as the basis of several imaging systems, including widefield
and linescan endomicroscopes. External users are welcome to make use of this 
code for other purposes, but be aware that it is not currently fully documented or 
tested outside of our specific applications. 

## Rough Guide

CAS must currently be downloaded from github or cloned using `git clone http://www.github.com/mikehugheskent/cas`.
Pyfibrebundle may either be installed with `pip install pyfibrebundle` or `git clone http://www.github.com/mikehugheskent/pyfibrebundle`.

Endomicroscope, CAS and PyFibreBundle should all sit in the same top-level folder, otherwise you will need to edit the paths at the top
of `src/endomicroscope.py`

To launch the GUI, run `src/endomicroscope.py`. Select the input camera from the 
drop-down menu in the 'Source' menu and click 'Live Imaging' to begin. 
It will obviously only work for cameras you have set up on your system - try 
the Webcam (if you have one) or Simulated Camera first. The Simulated Camera 
can load a sequence of images from a tif stack in order to simulate camera 
acquisition. Alternatively, select the 'File' source to load in a saved image
or tif stack. See CAS documentation for more details.

At first use, or when changing probes, perform a Bundle Calibration in the Settings mene, by clicking 'Acquire background' and 'Calibrate Bundle'.

To use with a linescan endomicroscope, ensure that `ls = True' near the top of the file. On first use, or after realignment,
it is necessary to calibrate the linescan using the Auto Calibration button in the Line Scanning menu. For this, ensure the
laser is on and the probe is pointing into empty space.

## Requirements
In addition to CAS and pyfibrebundle requirements (including drivers for the camera), for use with a linescan endomicroscope 
using a NI DAQ, endomicroscope requires:
* nidaqmx (National Instruments)


