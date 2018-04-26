# Use to try to open and read in emccd data from FIREBall-2
#
#

#Method to wrap print+file output together
def log(string):
	print(string)
	logfile.write(string+'\n')


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
	prefix = '.png'
	fnum = 1		# start figure number here
	mxnum = 12	# Max. number of plots per figure

	fig = plt.figure()

	# Loop through each spectrum coords.
	for i in range(0,len(x_spec)):
		j = i%mxnum
		print j

		ax = fig.add_subplot(6,2,j+1)

		xrg = [x_spec[i]-x_end,x_spec[i]]
		yrg = [y_spec[i]-y_wid[i]/2,y_spec[i]+y_wid[i]/2]
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
			plt.savefig("%s_%02i%s" % (file,fnum,prefix), format='png')
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




def read_fits(filename):
	# Open fits with astropy
	hdulist = fits.open(filename)
	print filename
	hdulist.info()	# No.    Name      Ver    Type      Cards   Dimensions   Format
									# 0  PRIMARY        1  Primary HDU   11   (3216, 2069)   int16
	data = hdulist[0].data
	hrd = hdulist[0].header		# Can do hdr.comments[' '] to check header comments

	hdulist.close()
	return data





def gaus(x, y):
	'''
	Make a 1-D Gaussian fit to model the detector read noise!
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
		#~ value[0,i] = x[i]
		#~ value[1,i] = y[i]
		#~ value[2,i] = width[i]

	return key,value



from astropy.io import fits
import time
from datetime import datetime
import os
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


# File location and name
directory = "C:\Users\Keri Hoadley\Documents\FIREBall-2\python\FIREBall-2 python\\170901_darks\\focus"   #"." #Directory to use
#~ directory = "C:\Users\Keri Hoadley\Documents\FIREBall-2\python\
							#~ FIREBall-2 python\\170907\\throughfocus"
filename_root = "events_field"	#"image" #Substring to find in filenames
num0 = 1			#File number you want to start on
delay = 10 			#Time to wait before moving on to next file
picklefile = 'fb2_fields_txtv1.pickle'

xlims = [1000,2100]		# Range where detector has spectral features
dx = 5		# Scan over sub-spot size pixels
zn_lines = [202.548, 206.423, 213.856]	# nm - Zn lamp spectral features

#Other variables
now = datetime.now()

field_spectra = dict()

quit = False
i = 0
num = num0

x_end = 950		# Define number of pixels in x-axis for spectral extraction

#Modifications
#directory = os.path.abspath(directory) #Make sure directory is absolute path

#Keep running program unless something sets break condition (quit=True)
while not(quit):
	filename = "%s%02i.fits" % (filename_root,num)			# If events_fieldsxx.fits
	plotfile = "spectra_%s%02i" % (filename_root,num)
	#~ filename = "%s%06i.fits" % (filename_root,num)			# If image000xxx or events000xxx

	#Create booleans to keep track of whether each file is found
	filefound = False

	#Run through all files in directory and try to match names
	# THIS CHECK IS FOR IMAGES
	for f in os.listdir(directory):
		if filename in f: filefound=True

	# No fits file found with correct name.
	# Re-look for fits file after delay
	if not filefound:
		print "File %s not found; sleeping..." % (filename)
		time.sleep(delay)

	# IF fits file found with correct name, then open and do operations
	elif filefound:
		# Read in image file - QUICKCHECK
		img = read_fits(os.path.join(directory,filename))
		# The data size read in won't be the correct size - Create a zero 2D array
		# and place the data array in the appropriate spot in it.
		data_arr = numpy.zeros( shape=[2069,3216] )
		data_arr[100:1900,1050:2100] = img
		img = data_arr

		data_tmp = img

		x_spec,y_spec,y_width = spectral_scan(data_tmp,xlims,dx)

		img = read_fits(os.path.join(directory,filename))
		# The data size read in won't be the correct size - Create a zero 2D array
		# and place the data array in the appropriate spot in it.
		data_arr = numpy.zeros( shape=[2069,3216] )
		data_arr[100:1900,1050:2100] = img
		img = data_arr

		# Plot data and overplot extraction boxes
		fig = plt.figure()
		ax1 = fig.add_subplot(1,1,1)
		ax1.set_xlabel('x - wavelength',weight='bold',size='large')
		ax1.set_xlim(400,2500)
		ax1.set_ylabel('y',weight='bold',size='large')
		ax1.set_title('Field %01i' % (num),weight='bold',size='x-large')
		ax1.set_axis_bgcolor('black')
		ax1.tick_params(labelsize=12)

		plt.imshow(img, norm=LogNorm(vmin=1, vmax=3), cmap='viridis', origin='upper')
		#~ plt.axvline(x=x_spec, linestyle='dashed', color='r')
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
		#~ cbar = plt.colorbar()
		#~ cbar.ax.set_ylabel('Counts')

		#~ plt.show()
		print "Saving plot to %s.png" % (plotfile)
		plt.savefig(plotfile+'.png',format='png')

		# Define dictionary key and values for field
		# explored here
		key,value = define_dictionary_elements(num,x_spec,y_spec,y_width)

		# Add new key and value to field spectra dictionary
		field_spectra[key] = value

		# Now, try to solve wavelength solution from first clean set of spectral
		# lines we come across per field
		for ii in range(0,len(x_spec)):
			xrg = [x_spec[ii]-x_end,x_spec[ii]]
			yrg = [y_spec[ii]-y_width[ii],y_spec[ii]+y_width[ii]]
			returncode,wv = define_wavelength(img,xrg,yrg,zn_lines)
			if returncode == 0:
				print "Wavelength array defined!"
				break
			else:
				print "No clean spectra extracted yet; continuing..."

		print "Plotting individual spectra..."
		plot_spectra(img,x_spec,x_end,y_spec,y_width,wv,plotfile)
		print "Finished plotting spectra"


		# If the last field, and all field spectra have been saved
		# the the dictionary keys/values,
		# Then save the dictionary to an output array (pickle?)
		if num == 4:
			print "All fields explored: Saving spectral extraction regions to pickle:"
			with open(picklefile, 'wb') as handle:
				pickle.dump(field_spectra, handle, protocol=pickle.HIGHEST_PROTOCOL)


		# Check that this worked?
		print field_spectra
		print
		print "Begin sleep..."
		time.sleep(delay)
		print 'End of sleep'
		num+=1







