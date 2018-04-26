# Use to try to open and read in emccd data from FIREBall-2
#
#

#Method to wrap print+file output together
def log(string):
	print(string)
	logfile.write(string+'\n')


def read_fits(filename,xrange,dx):
	# Open fits with astropy
	hdulist = fits.open(filename)
	print filename
	hdulist.info()	# No.    Name      Ver    Type      Cards   Dimensions   Format
											# 0  PRIMARY       1 Primary HDU   11   (3216, 2069)   int16 (rescales to uint16)
	data = hdulist[0].data
	hrd = hdulist[0].header		# Can do hdr.comments[' '] to check header comments

	# PLot the resulting 2D image to pick out a spectral line to collapse to 1d spectrum
	# plot the 2d histogram
	fig = plt.figure()
	ax1 = fig.add_subplot(1,1,1)
	ax1.set_xlabel('x',weight='bold',size='x-large')
	ax1.set_ylabel('y',weight='bold',size='x-large')
	ax1.set_axis_bgcolor('black')
	ax1.tick_params(labelsize=18)
	#ax1.set_title('CLICK ON SPECTRAL LINE TO ANALYZE')

	#~ data = numpy.fliplr(data)
	plt.imshow(data, norm=LogNorm(vmin=1, vmax=3), cmap='viridis', origin='upper') # inferno - good    [:,xrange[0]:xrange[1]]
	#~ plt.imshow(data, norm=LogNorm(vmin=15000, vmax=20000), cmap='viridis')#, origin='lower') # inferno - good
	cbar = plt.colorbar()
	cbar.ax.set_ylabel('Counts')
	#~ plt.show()


	# Collapse along x, y axes to find: 1. what spectral box size is around,
	# 2. What the spectrum looks like
	xr=numpy.arange(xrange[0],xrange[1])
	extract_region_start = int(xrange[1] - (xrange[1]-xrange[0])*dx)
	print extract_region_start
	yr=numpy.arange(0,numpy.size(data[:,0]))
	x_collapse=numpy.zeros( numpy.size(yr) )
	y_collapse=numpy.zeros( numpy.size(xr) )
	# Collapses in x-axis to LOCATE y-axis POSITIONS OF SPECTRA
	for j in range(0,numpy.size(yr)):
		x_collapse[j] = numpy.sum( data[yr[j],extract_region_start:xrange[1]] )		#xrange[0]:xrange[1]
	fig2=plt.figure()
	axx = fig2.add_subplot(1,1,1)
	axx.set_xlabel('y-pixels',weight='bold',size='x-large')
	axx.set_ylabel('Counts',weight='bold',size='x-large')
	#~ axx.set_axis_bgcolor('black')
	axx.tick_params(labelsize=18)
	#~ axx.set_title("Spectral extraction: x-pix = %04i - %04i" % (extract_region_start, xrange[1]),labelsize="large")
	plt.plot(yr,x_collapse,drawstyle="steps-mid",color='k')


	# Find peak(s) in x_collapse within xrange --> First extraction of field spectra
	peakind = signal.find_peaks_cwt(x_collapse,numpy.arange(1,15))
	peakind = peakind[numpy.where(x_collapse[peakind] > 0)]
	print peakind, yr[peakind],x_collapse[peakind]
	print numpy.size(peakind)
	# plot in x_collapse
	for i in peakind:
		plt.axvline(x=yr[i],color='r',linestyle='dashed')

	# DO for peakind[0] only
	fig3 = plt.figure()
	cnt = 0
	for sp in range(0,numpy.size(peakind)):
		sz = numpy.size(peakind)
		print cnt+1, (sp%2)+1, sp+1
		axy = fig3.add_subplot( sz/2, 2, cnt+1 )
		axy.set_title('y = %04i' % (peakind[sp]),size='small')
		axy.set_xlabel('x-pix',weight='bold',size='x-large')
		for i in range(0,numpy.size(xr)):
			y_collapse[i] = numpy.sum( data[peakind[sp]-10:peakind[sp]+10,xr[i]] )
			data[peakind[sp]-10:peakind[sp]+10,xr[i]] = 0
		plt.plot(xr,y_collapse,drawstyle="steps-mid",color='k')
		#~ if (sp%2) == 0:
		cnt += 1


	#~ axy = fig3.add_subplot(numpy.size(peakind)1,)
	#~ axx.set_xlabel('x',weight='bold',size='x-large')
	#~ axx.set_ylabel('y',weight='bold',size='x-large')
	#~ axx.tick_params(labelsize=18)
	#~ axx.set_title('Spectral Extract at y = %04i' % (peakind[0]),size='large')

	# See if setting data where spectra are extracted == 0 worked
	fig = plt.figure()
	ax1 = fig.add_subplot(1,1,1)
	ax1.set_xlabel('x',weight='bold',size='x-large')
	ax1.set_ylabel('y',weight='bold',size='x-large')
	ax1.set_axis_bgcolor('black')
	ax1.tick_params(labelsize=18)
	#ax1.set_title('CLICK ON SPECTRAL LINE TO ANALYZE')

	#~ data = numpy.fliplr(data)
	plt.imshow(data, norm=LogNorm(vmin=1, vmax=3), cmap='viridis', origin='upper') # inferno - good    [:,xrange[0]:xrange[1]]
	#~ plt.imshow(data, norm=LogNorm(vmin=15000, vmax=20000), cmap='viridis')#, origin='lower') # inferno - good
	cbar = plt.colorbar()
	cbar.ax.set_ylabel('Counts')

	plt.show()


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

	popt,pcov = curve_fit(gaus1d,x_half,y_half,p0=[theta_init[0],theta_init[1],theta_init[2]])

	print popt
	print
	print pcov
	print
	# Find chi2 of the gaussian with the theta parameters
	gaussian = []
	for i in range(0,len(x)):
		gaussian.append( popt[0]*numpy.exp( (-1)*( ( (x[i]-popt[1])**2/(2*popt[2]**2) ) ) ) )

	chisq = scipy.stats.chisquare(gaussian)

	print 'Chi**2: ', chisq

	# Find the CDF of chi2, and determine the PTE based on this CDF value
	# Define the DOF of the data set, where DOF = # of data points - # of parameters
	dof = len(y) - len(popt)
	chicdf = scipy.stats.chi2.cdf(chisq,dof)
	pte = 1. - chicdf
	fwhm=popt[2]*2*numpy.log(2.)
	print "DOF:", dof
	print 'PTE: ', pte
	print 'FWHM',fwhm

	plt.plot(x, gaussian, drawstyle='steps-mid',color='g')
	#plt.show(block=False)
	#time.sleep(10)

	return popt[2]






from astropy.io import fits
import time
from datetime import datetime
import os
import numpy
import matplotlib.pyplot as plt
#from matplotlib.pyplot import figure, show
from matplotlib.colors import LogNorm
from scipy.optimize import curve_fit
from scipy.optimize import leastsq
import scipy.stats
from scipy import signal

# File location and name
directory = "C:\Users\Keri Hoadley\Documents\FIREBall-2\python\FIREBall-2 python\\170901_darks\\focus"   #"." #Directory to use
#~ directory = "C:\Users\Keri Hoadley\Documents\FIREBall-2\python\FIREBall-2 python\\170907\\throughfocus"
filename_root = "events_field"	#"image" #Substring to find in filenames
num0 = 1			#File number you want to start on
delay = 10 			#Time to wait before moving on to next file

xlims = [1000,2000]		# Range where detector has spectral features
spectra_extraction_regions = 0.25		# Use quarter-sized regions to slowly extract spectra from images

#Other variables
now = datetime.now()


quit = False
i = 0
num = num0

#Modifications
#directory = os.path.abspath(directory) #Make sure directory is absolute path

#Keep running program unless something sets break condition (quit=True)
while not(quit):
	filename = "%s%02i.fits" % (filename_root,num)			# If events_fieldsxx.fits
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
		data = read_fits(os.path.join(directory,filename),xlims,spectra_extraction_regions)
		print type(data)


		time.sleep(delay)
		print 'End of sleep'
		num+=1







