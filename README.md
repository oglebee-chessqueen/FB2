FB2 Scripts (written by K. Hoadley) for calibrations, analysis, and telemetry for the FIREBall-2 balloon experiment
Folders within the FB2 master repository:

Folders
-------
1 MBit telemetry
Quicklook
Analysis
Calibration


FB2 Calibrations

This repository will be used to store scripts to analyze different calibration tests/runs data taken with the science detector and to produce tangible results that can be referred to later.

- Current planned calibration/testing that will need automated scripts:
- focus of spectrograph
- diagnsotics of spectrograph images: Spectral Range, Dispersion, PSF
- Photon transfer curve analysis
- Dark noise, Read noise analysis
- Gain --> e/e conversion
-  Auto-collimation: focus curves






FB2 - Quicklook

The quickloop software is a way to check the FB2 observations during flight. 
The current versions of the software uses properties of calibration science detector images to derive field slit positions and wavelength solutions for each spectrum. 

IT IS NOT DESIGNED TO DO MORE DETAILED ANALYSIS OF THE FB2 DATA, which will be required after the flight to fully analyze the flight data.

Current versions of scripts:

fb2_image2events.py: Converts the science detector image into a photon-counted image, saving to an events fits file. (e.g., events_field01.fits - photon counted FITS file for science field 1)

fb2_fields_v2.py: Reads in the photon-counted image and scans from right-to-left across the image to identify the location/start of a spectrum. Currently, I use the Zinc lamp spectra imaged with the science detector to find where slits exist in each field. This script also outputs the positions of each spectrum in a python PICKLE file, which can be read-in for the spectral extraction, wavelength solution, and quicklook spectra script(s).

fb2_define_spectra_locations(txtv1).py: Either reads in the PICKLE file produced in fb2_fields_v2.py or finds the location the each spectrum with the spectral scan function, but also collapses the spectrum within each defined slit region and creates a wavelength solution based on the locations and laboratory wavelengths of the 3 Zinc lines used in the calibration images. Outputs images of the slit regions extracted from each FB2 science field, numbering each slit (ex: field3_image.png), and produces the spectrum within each slit (along with number identifier).

Things I want to do/improve:

- Use known positions of the science mask slits (provided by David) to create a known mask of all slit positions (and sizes) for the science detector.
- Check with Vincent that the wavelength solutions determined using the 3 emission lines match (or are in good agreement) with optical models of FB2
- Output extracted regions to FIT file (for people to access on their own), including wavelength solution(?)
Per field, per slit: Hard-code in redshift to correct NUV wavelength solution --> FUV
- Get requests from the group: What does everyone want to see right away from the flight data? What plots would be informative? Are there any outputs wanted right away, for people to manipulate on their own?


Other improvements suggested:

Bruno: 

       - stacking within a field (inclusion criteria TBD) and for individual and stacked:
       
       - galaxy subtracted image 
       
       - galaxy subtracted  total flux in the line(s)
       
       
Vincent:

       - ***Include calibraiton software written to characterize focus, slit scan, detections, etc.)
        
         - ***Incorporate disperion characteristics of spectra as a function of position on the detector

*** these I would have to work with Vincent/Didier on to best implement them
