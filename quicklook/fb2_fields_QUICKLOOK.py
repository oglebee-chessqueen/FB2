##
##
## QUICKLOOK Analysis of FIREBall-2 Fields During Flight:
#
# 1. Read in data (TXT) files from transmitter (on voldy: Ground computer)
#	2. Create histrogram of cts:
#			- Fit Gaussian to Read-Noise bump
#			- Determine where 5-sig is from Read-Noise
#			- Add events +1 per pixel with cts >= 5-sig location
# 3. Save events.fits to: events_fieldxx.fit, and events_image000xxx.fits
# 4. Read in the pickle file that was created by taking the total events array
#		 	(for a given field), and performing the following:
#			- Scan along x-axis for peaks appearing in the data
#			- For each peak, determine if the start of a spectrum or not
#			- If it is, place spectral box there
#			- Pickle file saves as a dictionary, with:
#						key = field
#						value = [x,y,y-width]
# 5. Plot (and save) events image + spectral boxes
# 6. Apply the pixel--to--wavelength solution (general), which was
#		 	originally determined from Zinc-lamp spectra on the ground.
# 7. Apply wavelength solution per field to all spectral boxes
#		 	and plot spectrum per box in an image (12 spectra/page)
# 8. Repeat process for all images coming in per field.
# (9. Apply Gillian's cosmic ray removal routine every 3 - 5 iterations?)
#

from astropy.io import fits
import time
from datetime import datetime, timedelta
import os
import sys
import numpy
import matplotlib.pyplot as plt
#from matplotlib.pyplot import figure, show
from matplotlib.colors import LogNorm
import matplotlib.patches as patches
from scipy.optimize import curve_fit
from scipy.optimize import leastsq
import scipy.stats
from scipy import signal
import pickle
import socket




def main():
	# File directories
	if os.name == "posix":
		dir = '/'
		# voldy:
		if socket.gethostname() == 'voldy':
			root = "/home/fireball2/dobc/data/"
		# dobby:
		elif socket.gethostname() == 'dobby':
			root = "/home/fireball2/fireball2-shared/data/dobc/ground/"
	elif os.name == "nt": # windows
		root = "C:\Users\\Keri Hoadley\\Documents\\FIREBall-2\\python"
		dir = '\\'
	else:
		print "Unrecognized platform, exiting."
		exit(1)
	directories = {
		#~ "img": "FBFlight",
		#~ "img": "FIREBall-2 python\\170901_darks\\focus",
		#~ "img": "test_python_receiver"+dir+"images",
		"img": "",
	}
	for key, value in directories.iteritems():
		directories[key] = os.path.normpath(os.path.join(root, value))+dir
	# File location and name
	filename_root_image = "image"	#"image" #Substring to find in filenames
	filename_root_event = "events_field"	#"image" #Substring to find in filenames
	if len(sys.argv) == 2:		# Define img no., then field no.
		print "Arguments called: ", sys.argv[1]
		num0 = int(sys.argv[1])
		field = 1
	elif len(sys.argv) == 3:
		print "Arguments called: ", sys.argv[1:]
		num0 = int(sys.argv[1])
		field = int(sys.argv[2])
	else:
		num0 = 0			# IMAGE File number you want to start on
		field = 1
	print "Initial starting number: ", num0
	print "Field of interest: ", field
	#~ num0 = 0			# IMAGE File number you want to start on
	#~ field = 1
	picklefile = 'fb2_fields_v1.pickle'		#os.path.join(root,'fb2_fields_v1.pickle')

	#Other variables
	now = datetime.now()
	quit = False
	#~ i = 0
	num = num0
	delay = 10 			#Time to wait before moving on to next file

	# Spectral diagnostic variables
	#~ xlims = [1000,2100]		# Range where detector has spectral features
	#~ dx = 5		# Scan over sub-spot size pixels
	#~ zn_lines = [202.548, 206.423, 213.856]	# nm - Zn lamp spectral features
	x_end = 950		# Define number of pixels in x-axis for spectral extraction
	pix2wave = numpy.poly1d([-3.53540853e-06, 2.58769939e-02, 1.93900741e+02])
	# Call ^ as pix2wave(xr)

	# Log progress of quicklook script
	logfile = "log_FB2QuicklookFIELDS_%02i%02i%02i_%02i%02i.log" % (now.year%100,now.month,now.day,now.hour,now.minute)
	logfile_gauss = "log_ReadOutParms_%02i%02i%02i_%02i%02i.log" % (now.year%100,now.month,now.day,now.hour,now.minute)
	log(logfile,"Checking directory: %s" % (directories["img"]+datetime.now().strftime("%y%m%d")))
	log(logfile,"File:     \t \t  Total Photon Events:")
	log(logfile_gauss,"File:   \t  \t  \t  Gaussian Parameters: ")
	log(logfile_gauss,"\t  \t  \t x0 (cts) \t stdev (cts) \t Gain \t")
	log(logfile_gauss,"---------------- \t -------- \t ----------- \t ------\t")

	#Keep running program unless something sets break condition (quit=True)
	while not(quit):
		#~ for key, value in directories.iteritems():
			#~ directories[key] = os.path.join(value, datetime.now().strftime("%y%m%d"))
		filename = "%s%06i.txt" % (filename_root_image,num)			# If events_fieldsxx.fits
		plotfile = directories["img"]+datetime.now().strftime("%y%m%d")+dir+"spectra_%s%02i" % (filename_root_event,field)

		#Create booleans to keep track of whether each file is found
		filefound = False

		#Run through all files in directory and try to match names
		# THIS CHECK IS FOR IMAGES
		for f in os.listdir(directories["img"]+datetime.now().strftime("%y%m%d")):
			if filename in f: filefound=True

		# No fits file found with correct name.
		# Re-look for fits file after delay
		if not filefound:
			print "File %s not found; sleeping..." % (filename)
			time.sleep(delay)

		# IF fits file found with correct name, then open and do operations
		elif filefound:
			'''
			PART 1: TURN IMAGE CTS --> PHOTON EVENTS
			----------------------------------------
			- Read in TXT file from file transfer
			- Create Histogram of counts over # of instances of counts
			- Fit Gaussian to Read Noise "bump"
			- Use sigma from Gaussian fit to set limit of where noise--> photons
			- Find where pixel cts >= 5sigma, and add photon event to event array
			- Save event array (image) to two fits files:
					1. events_fieldxx.fits -- total events counted in a given field
					2. events_000xxx.fits -- events array created from image000xxx.txt
			- Save histrogram to output plot.
			'''
			# Read in image file
			log(logfile,"Current file: %s" % (filename))
			data = read_fits(os.path.join(directories["img"]+datetime.now().strftime("%y%m%d"),filename),logfile)

			max=numpy.max(data)
			x_range = numpy.arange(0,max+1,1)
			y_range = numpy.zeros( numpy.size(x_range ) )

			for i in numpy.ravel(data):
				y_range[int(i)] += 1
			y_range2=numpy.log10(y_range)
			ymx = numpy.max(y_range2)
			print ymx

			for i in range(0, numpy.size(y_range2)):
				if  numpy.isnan(y_range2[i])=='True' or numpy.isinf(y_range2[i])=='True' :
					y_range2[i]=0
				elif  y_range2[i]==float('-inf') or y_range2[i]==float('inf'):
					y_range2[i]=0

			fig = plt.figure()	#plt.gcf()
			fig.set_size_inches(10.5, 8.5)
			ax1 = fig.add_subplot(1,1,1)
			ax1.set_xlabel('pixel cts',weight='bold',size='large')
			ax1.set_ylabel('Total # of cts instances',weight='bold',size='large')
			ax1.set_axis_bgcolor('black')
			ax1.tick_params(labelsize=12)
			ax1.set_title(filename[-10:-4])
			plt.plot(x_range,y_range2,drawstyle='steps-mid')


			x_range_gauss =numpy.arange(numpy.where(y_range2==ymx)[0] -500, numpy.where(y_range2==ymx)[0] +500)
			y_range_gauss = y_range2[x_range_gauss]


			# YES!

			plt.plot(x_range_gauss, y_range_gauss, drawstyle='steps-mid',color='r')
			peak, x0, sig = gaus(x_range_gauss, y_range_gauss)
			#~ plt.xlim(0,max)
			plt.xlim(10000,30000)
			plt.ylim(0,numpy.max(y_range2))


			# For now, set stdv = num.size(x)/6.
			stdv = sig*5 	#num.size(x_range_gauss)/6.
			photon_list = photon_events(data,stdv+x0)
			# The data size read in won't be the correct size - Create a zero 2D array
			# and place the data array in the appropriate spot in it.
			img = numpy.zeros( shape=[2069,3216] )
			print numpy.shape(photon_list)

			img[70:numpy.size(photon_list[:,0])+70,1000:2150] = photon_list
			#~ photon_list = img

			print numpy.shape(photon_list)
			lin_start = numpy.fix(stdv+numpy.median(x_range_gauss))			# Start 5-sigma away from read-out Gaussian shape
			lin_start = numpy.int_(lin_start)
			lin_end = lin_start+1000

			lnfit = numpy.polyfit(x_range[lin_start:lin_end],y_range2[lin_start:lin_end],1)
			yfit = map(lambda x: lnfit[0]*x + lnfit[1], x_range[lin_start:])
			yfit=numpy.array(yfit)
			#~ endln = x_range[numpy.where(yfit<0)[0]+lin_start]
			#~ endln = numpy.int_(endln[0])


			gain = (-1./lnfit[0])
			print gain
			if numpy.isinf(abs(gain)):
				gain = 0
			log(logfile_gauss,'%s \t %0.2i \t \t %0.2f \t %05i' % (filename, x0, sig, gain))

			#~ ysum = numpy.sum(10**(y_range2[lin_start:endln]))
			ysum = numpy.sum(10**(y_range2[lin_start:]))
			log(logfile,"%s \t \t %06i" % (filename, ysum))

			'''
			Store new events data array into its own fits file for later use.

			ALSO, chances are that events.fits already exists,
				so we want to write two files:
			1. Write to events+%06i.fits % num
			2. Read in events_fieldxx.fits
			3. Events_update = events_previous + events_current
			4. Write new Events_update to evets_fieldxx.fits

			Only write events to events+num.fits and events_fieldxx.fits
			'''
			file1 = "events%06i_170924.fits" % (num)
			file1 = os.path.join(directories["img"]+datetime.now().strftime("%y%m%d"),file1)
			file2 = "events_field%02i_170924.fits" % (field)
			file2 = os.path.join(directories["img"]+datetime.now().strftime("%y%m%d"),file2)
			if num == num0:		# Special case: first file, so no events file exist yet
				returncode = write_newfits(file2,img)
			else:		# All other cases: events have been recorded
				returncode, photon_list = write_fits(file2,img,num)

			plt.plot(x_range[lin_start:],y_range2[lin_start:],drawstyle='steps-mid',color='y')
			# overplot line fit
			plt.plot(x_range[lin_start:],yfit,linestyle='dashed',color='k')
			#~ plt.show()
			plt.savefig(os.path.join(directories["img"]+datetime.now().strftime("%y%m%d"),filename+'_HISTOGRAM.eps'),dvi=300,format='eps',orientation='landscape')
			plt.clf()




			'''
			PART 2: QUICK ANALYSIS OF FIELD SPECTRA
			----------------------------------------
			With photon events found from a given image (of a specified field):
			- Read in pre-defined dictionary of spectral boxes:
					key = field #
					value = [x,y,ywidth]
					spectral boxes defined as: x = [x[i]-x_end,x[i]]
																		 y = [y[i]-ywidth[i],y[i]+ywidth[i]]
			- Plot image area with spectral boxes --> save to output file
			- Use wavelength solution to create spectra from defined boxes
			- Plot spectra in output files (12 spectra per file)
			'''
			# The data size read in won't be the correct size - Create a zero 2D array
			# and place the data array in the appropriate spot in it.
			#~ img = numpy.zeros( shape=[2069,3216] )
			#~ img[70:numpy.size(photon_list[:,0])+70,1000:2150] = photon_list

			# Read in pickle file
			pkf = open(picklefile,'rb')
			dict = pickle.load(pkf)
			field_spec = dict[field]
			x_spec = numpy.int_( field_spec[0,:] )
			y_spec = numpy.int_( field_spec[1,:] )
			y_width = numpy.int_( field_spec[2,:] )

			# Plot data ONLY
			fig = plt.figure()
			fig.set_size_inches(10.5, 8.5)
			ax1 = fig.add_subplot(1,1,1)
			ax1.set_xlabel('x - wavelength',weight='bold',size='large')
			ax1.set_xlim(400,2500)
			ax1.set_ylabel('y',weight='bold',size='large')
			ax1.set_title('Field %01i' % (field),weight='bold',size='x-large')
			ax1.set_axis_bgcolor('black')
			ax1.tick_params(labelsize=12)
			plt.imshow(img, norm=LogNorm(vmin=1, vmax=3), cmap='viridis', origin='upper')
			log(logfile, "Saving plot to %s.png" % (plotfile))
			plt.savefig(plotfile+'_NOBOXES.eps', dpi=600, format='eps')

			# Plot data and overplot extraction boxes
			fig = plt.figure()
			fig.set_size_inches(10.5, 8.5)
			ax1 = fig.add_subplot(1,1,1)
			ax1.set_xlabel('x - wavelength',weight='bold',size='large')
			ax1.set_xlim(400,2500)
			ax1.set_ylabel('y',weight='bold',size='large')
			ax1.set_title('Field %01i' % (field),weight='bold',size='x-large')
			ax1.set_axis_bgcolor('black')
			ax1.tick_params(labelsize=12)
			plt.imshow(img, norm=LogNorm(vmin=1, vmax=3), cmap='viridis', origin='upper')
			for k in range(0,len(x_spec)):
				ax1.add_patch(
					patches.Rectangle(
						(x_spec[k]-x_end, y_spec[k]-y_width[k]),
						x_end,
						2*y_width[k],
						fill=False ,     # remove background
						edgecolor='red'
						)
				)
				plt.text(x_spec[k]+10, y_spec[k],'%02i' % (k+1),color='red')

			log(logfile, "Saving plot to %s.png" % (plotfile))
			plt.savefig(plotfile+'_SPECTRALBOXES.eps', dpi=600, format='eps')


			# Now, try to solve wavelength solution from first clean set of spectral
			# lines we come across per field
			xrg = numpy.arange(0,x_end)
			wv = pix2wave(xrg)

			plot_spectra(img,x_spec,x_end,y_spec,y_width,wv,plotfile)

			# Check that this worked?
			print "Begin Sleep..."
			time.sleep(delay)
			print "End sleep..."
			num+=1






# Wrap print+file output together
def log(logfile, string):
	print(string)
	with open(logfile, 'a') as f:
		f.write(string + '\n')



def define_wavelength(data,xrange,yrange,cal_wave):
	'''
	Use to define wavelength solution between pixels and wavelength.
	data - 2D image array
	xrange = 2-element array, defining boundaries in x-axis for spectrum
	yrange = 2-element array, defining boundaries in y-axis for extraction
	cal_wave = list of wavelengths for reference lines
	'''
	# Get xr, y_coll from spectral_collapse
	xr, y_coll = spectral_collapse(data,xrange,yrange)

	# Reverse xr, y_coll to be in correct left--> right orientation
	xr = numpy.arange( 0, numpy.size(xr) ) #numpy.flipud(xr)
	y_coll = numpy.flipud(y_coll)

	# Plot what the spectrum looks like
	fig3 = plt.figure()
	axy = fig3.add_subplot( 1,1,1 )
	axy.set_title('y = %04i - %04i' % (yrange[0],yrange[1]),size='small')
	axy.set_xlabel('x-pix',weight='bold',size='x-large')
	axy.set_ylabel('x-pix',weight='bold',size='x-large')
	plt.plot(xr,y_coll,drawstyle="steps-mid",color='k')
	#~ plt.gca().invert_xaxis()

	# Find how many peaks show up in the spectrum
	peakind = signal.find_peaks_cwt(y_coll[0:925],numpy.arange(1,15))
	#~ if numpy.size(peakind) == 0:
		#~ print "No peaks found - continuing"
	peakind = peakind[numpy.where(y_coll[peakind] > 0)]
	# Check if there are 3 peaks only - if so, plot their locations in the figure
	if numpy.size(peakind) == len(cal_wave):
		print "3 peaks found!: ", peakind
		returncode = 0
		for peak in peakind:
			plt.axvline(x=xr[peak],color='r',linestyle='dashed')
		plt.show()
		# Map the cal_wave lines to the peaks
		# 1. 1D fit peakind --> cal_wave (wave = a*pix + b)
		fit1d = numpy.polyfit(peakind,cal_wave,1)		# output: a, b coeffs
		p1d = numpy.poly1d(fit1d)			# Fits the 1d coeffs to output array

		# 2. Fit 2d to peakind <--- Better than 1D
		fit2d = numpy.polyfit(peakind,cal_wave,2)		# output: a, b, c coeffs
		p2d = numpy.poly1d(fit2d)			# Fits the 2d coeffs to output array
		print "Polynomial coefficients: ", fit2d

		# New plot: wave vs. pixel fit, with cal_wave and peakind points
		fig = plt.figure()
		axy = fig.add_subplot( 1,1,1 )
		axy.set_title('Pixel-to-Wavelength conversion: %04i - %04i' % (yrange[0],yrange[1]),size='small')
		axy.set_ylabel('Wavelength',weight='bold',size='large')
		axy.set_xlabel('Pixels',weight='bold',size='large')

		plt.plot(peakind, cal_wave, 'ro', linestyle='None', ms=8)
		plt.plot(xr, p1d(xr), linestyle='dashed', color='b')
		plt.plot(xr, p2d(xr), linestyle='dashed', color='g')
		plt.show()

		wave_array = p2d(xr)

	else:
		"No. of peaks found not correct -- continuing"
		returncode = 1
		wave_array = 0
		plt.show()

	return returncode, wave_array




def spectral_collapse(data,xrange,yrange):
	'''
	Use to show what the spectrum within the defined "box" looks like
	'''
	# Collapse along y-axis to create spectrum;
	# Define a "box" around the image area to do so.
	xr=numpy.arange(xrange[0],xrange[1])
	y_collapse=numpy.zeros( numpy.size(xr) )

	for i in range(0,numpy.size(xr)):
		y_collapse[i] = numpy.sum( data[yrange[0]:yrange[1],xr[i]] )

	return xr, y_collapse




def plot_spectra(data,x_spec,x_end,y_spec,y_wid,wavelength,file):
	'''
	Plot the extracted regions from the field image.
	First, clear the plot call (plt.clr()), in case anything is left.
	Define each figure as a subplot with 12 spots for figures.
	Define x,y axis labels.
	Then, define spectral regions.
	Plot spectral regions.
	Once 12 plots have been added, define a new figure and restart.
	Save figures to output file.
	'''
	plt.clf()
	prefix = '.eps'
	fnum = 1		# start figure number here
	mxnum = 12	# Max. number of plots per figure

	fig = plt.figure()
	fig.set_size_inches(10.5, 8.5)

	# Loop through each spectrum coords.
	for i in range(0,len(x_spec)):
		j = i%mxnum
		print j

		ax = fig.add_subplot(6,2,j+1)

		xrg = [x_spec[i]-x_end,x_spec[i]]
		yrg = [y_spec[i]-y_wid[i]/2,y_spec[i]+y_wid[i]/2]

		print xrg, yrg
		x, y = spectral_collapse(data,xrg,yrg)		# Define spectra
		y = numpy.flipud(y)		# Invert for correct orientation
		# take out spectrum from data to try to not contaminate other features
		data[yrg,xrg] = 0

		plt.plot(wavelength,y,drawstyle="steps-mid",color='k')
		plt.text(195,numpy.max(y)-15,str(i+1),weight='bold')
		if j == 10 or j == 11:
			ax.set_xlabel('Wavelength (nm)',weight='bold',size='small')
		if j%2 == 0:
			ax.set_ylabel('Counts',weight='bold',size='small')

		if (j == 11) or (i == len(x_spec)-1):
			plt.savefig("%s_1DSPECTRA_%02i%s" % (file,fnum,prefix), dpi=600, format='eps')
			fnum += 1
			plt.clf()
		else:
			continue


	return





def spectral_scan(data,xrange,dx):
	'''
	Use to scan from xrange[1] --> xrange[0] in incremenets of dx (defined in pixels)
	'''
	# Define range over p-pixels to collapse along x
	yr = numpy.arange(0, numpy.size(data[:,0]))
	scan = (xrange[1] - xrange[0]) / dx
	x_collapse = numpy.zeros(shape=[numpy.size(yr),scan])
	#~ print "Shape of x_collapse:", numpy.shape(x_collapse)
	extract_range = numpy.arange(xrange[1],xrange[0],-1*dx)

	# Define empty array to define "start" x,y pixels of each spectrum
	x_spec = []
	y_spec = []
	wd_spec = [] # Width of the spectral feature

	# Collapses in x-axis to LOCATE y-axis POSITIONS OF SPECTRA
	for i in range(0,numpy.size(extract_range)-1):
		x1 = extract_range[i]
		x2 = extract_range[i+1]		# x2 is smaller than x1; going from 2000 --> 1000
															# in increments of dx
		print x2, x1

		for j in range(0,numpy.size(yr)):
			x_collapse[j,i] = numpy.sum( data[yr[j],x2:x1] )		#xrange[0]:xrange[1]

		# Find peak(s) in x_collapse within xrange -->
		#			First extraction of field spectra
		peakind = signal.find_peaks_cwt(x_collapse[:,i],numpy.arange(1,15))
		if numpy.size(peakind) == 0:
			continue
		peakind = peakind[numpy.where(x_collapse[peakind,i] > 0)]
		if numpy.size(peakind) != 0:		# Test to see if there are any elements left in peakind

			for ii in peakind:
				print "Fitting Gaussian for peak(s) found..."
				parms = gaus(yr[ii-40:ii+40], x_collapse[ii-40:ii+40,i])
				fwhm = int(abs(parms[2])*2*numpy.log(2.)+4)
				if (abs(parms[2]) >= 3.5) and (abs(parms[2]) < 15):
					print "Stdv = %0.2f -- Real point; Saving to spectral box definitions!" % (parms[2])
					x_spec.append(x2+350)
					y_spec.append(ii)
					wd_spec.append(fwhm)#*2
					# Take out spectral feature from: x2 + 100 --> x2 - 600
					data[ii-fwhm:ii+fwhm,x2-600:x2+100] = 0
		else:
			print "No peaks found between %04i - %04i: Continue to next segment..." % (x2,x1)

	print "Total spectral features found: %02i" % (len(x_spec))

	return x_spec, y_spec, wd_spec




def read_fits(filename,logfile):
	# Open fits with astropy
	if filename.endswith('.fits'):
		hdulist = fits.open(filename)
		hdulist.info()	# No.    Name      Ver    Type      Cards   Dimensions   Format
											# 0  PRIMARY       1 Primary HDU   11   (3216, 2069)   int16 (rescales to uint16)
		data = hdulist[0].data
		hrd = hdulist[0].header		# Can do hdr.comments[' '] to check header comments
		hdulist.close()
	# Else, if a text file, open with numpy.loadtxt
	elif filename.endswith(".txt"):
		# Try to read in min value from file
		try:
			lines = open(filename).readlines()
			fields1 = lines[2].split()
			fields2 = lines[3].split()
			fields3 = lines[4].split()
			min1 = fields1[1]
			min2 = fields2[1]
			min3 = fields3[1]
			if min1 == min2 or min1 == min3:
				min = numpy.int_(min1)
			elif min2 == min3:
				min = numpy.int_(min2)
			else:
				min = numpy.int_(min3)
			if not (min1 == min2 == min3):
				raise ValueError("****CHECK: min value Corruption in File:")
		except ValueError as e:
			log(logfile, "%s %s" % (repr(e), filename))
		if not min:
			min = 12500
		#~ # Try to read in min value from file
		#~ try:
			#~ lines = open(filename).readlines()
			#~ field = lines[2].split()
			#~ min = numpy.int_(field[1])
			#~ print type(min)
		#~ except:
			#~ print "Couldn't find min; try next line:"
			#~ try:
				#~ lines = open(filename).readlines()
				#~ field = lines[3].split()
				#~ min = field[1]
				#~ min = numpy.int_(field[1])
				#~ print type(min)
			#~ except:
				#~ print "Couldn't find min AGAIN; try last line..."
				#~ try:
					#~ lines = open(filename).readlines()
					#~ field = lines[4].split()
					#~ print field
					#~ min = field[1]
					#~ min = numpy.int_(field[1])
				#~ except:
					#~ print "Setting min to generic value: 12500"
					#~ min = 12500
		#~ print min
		# Open with numpy load function
		cols = numpy.arange(0,1150)		# Define number of column in data
		data = numpy.genfromtxt(filename,comments="#",skip_header=5,usecols=cols,filling_values=(-1*min),invalid_raise=False)
		data += min

		print "Shape of the image from 1 Mbit file: ",numpy.shape(data)

	return data



def gaus(x, y):
	'''
	Make a 1-D Gaussian fit to model the detector read noise and peaks in x-scan.
	'''
	# Initialize theta parameters
	theta_init = [numpy.max(y), numpy.max(x), numpy.size(x)/6.]

	# Determine uncertainties from the y-data.
	sigk = numpy.sqrt(y)		#num.ones(num.size(y))

	x_half = x[0:3*len(x)/4]
	y_half = y[0:3*len(x)/4]
	sigk_half = sigk[0:3*len(x)/4]

	def gaus1d(x,a,x0,sigma):
		return a*numpy.exp(-(x-x0)**2/(2*sigma**2))

	# Curvefit - try, or get a RunTimeError and pass
	try:
		popt,pcov = curve_fit(gaus1d,x_half,y_half,p0=[theta_init[0],theta_init[1],theta_init[2]])
	except RuntimeError:
		print "Gaussian fit RunTimeError -- no spectral feature"
		popt = numpy.array( [0,0,0] )
		pcov = numpy.array( [[0,0,0],[0,0,0],[0,0,0]] )
		pass

	return popt




def photon_events(data,cts_5sig):
	'''
	Using the cut-off counts in a pixel in data (cts_5ig), create a new 2D array that:
			0 - counts in pixel < cts_5sig
			1 - counts in pixel >= cts_5sig
	'''
	events = numpy.zeros( shape=numpy.shape(data) )
	events[numpy.where( (data >= cts_5sig) & (data < 30000) )] += 1
	print "Total counts from events: ", numpy.size(numpy.where( (data >= cts_5sig) ))

	return events




# 1. If creating new file, do this part:
def write_newfits(file,events):
	'''
	Using the new photon-counting array created by the 5-sig line fit,
	  open and write to a fits file.
	    (IF this is the first image taken in a new field;
	    otherwise, use write_fits function)
	'''
	try:
		hdu = fits.PrimaryHDU(events)
		hdulist = fits.HDUList([hdu])
		hdulist.writeto(file)
		print "Creating %s SUCCESS!" % (file)
		returncode=0
	except:
		# If writing a new file failed:
		print "Creating %s FAILED" % (file)
		returncode=1
	return returncode



# 2. If saving changes to already created file, do this part:
def write_fits(file,events,event_number):
	'''
	Read in previous photon events array.
	Update by adding new photon array to events array.
	Save fits file with new events array.
	'''
	try:
		print "Opening %s..." % (file)
		hdulist=fits.open(file,mode='update')
		print "...Opened! \n Updating Events..."
		#~ old_events = hdulist[0].data
		print numpy.shape(hdulist[0].data), numpy.shape(events)
		hdulist[0].data = hdulist[0].data + events
		print "Updated Events..."
		hdulist.flush()		# Should update file with new events array
		new_events = hdulist[0].data
		hdulist.close()
		print "Updating %s SUCCESS!" % (file)
		#~ new_events = old_events + events
		returncode=0
	except:
		print "Update to %s FAILED" % (file)
		returncode=1

	return returncode, new_events



def define_dictionary_elements(field,x,y,width):
	'''
	Define dictionary keys and values for spectral
	boxes per field.
	Define key as the field number (1,2,3,4)
	Define values as a 2D array with:
			1D = three elements (x,y,width)
			1D length = # of spectral boxes in field
	'''
	value = numpy.empty( shape=[3,len(x)] )
	key = field
	for i in range(0,len(x)):
		value[:,i] = [x[i],y[i],width[i]]

	return key,value







######### MAIN PROGRAM #########
if __name__ == "__main__":
	main()
