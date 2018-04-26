# Use to try to open and read in emccd data from FIREBall-2
#
#

#Method to wrap print+file output together
# Wrap print+file output together
def log(logfile, string):
	print(string)
	with open(logfile, 'a') as f:
		f.write(string + '\n')


def fields():
	'''
	Use this function to define which field the image s are taken in.
	Each field has its own set of UV slits.
	This function points to whicheven field we are in so we can align spectral extraction boxes around the
	UV spectra of different points in/outside of galaxies.
	'''



def read_fits(filename):
	# Open fits with astropy
	hdulist = fits.open(filename)
	hdulist.info()	# No.    Name      Ver    Type      Cards   Dimensions   Format
											# 0  PRIMARY       1 Primary HDU   11   (3216, 2069)   int16 (rescales to uint16)
	data = hdulist[0].data
	hrd = hdulist[0].header		# Can do hdr.comments[' '] to check header comments
	#~ print "Size: ", numpy.size(data[:,0]), numpy.size(data[0,:])
	#~ print "Shape: ", numpy.shape(data)

	#~ # Plot the resulting 2D image to pick out a spectral line to collapse to 1d spectrum
	#~ # plot the 2d histogram
	#~ fig = plt.figure()
	#~ ax1 = fig.add_subplot(1,1,1)
	#~ ax1.set_xlabel('x',weight='bold',size='x-large')
	#~ ax1.set_ylabel('y',weight='bold',size='x-large')
	#~ ax1.set_axis_bgcolor('black')
	#~ ax1.tick_params(labelsize=18)
	#~ #ax1.set_title('CLICK ON SPECTRAL LINE TO ANALYZE')


	#~ plt.imshow(data, norm=LogNorm(vmin=12500, vmax=14000), cmap='inferno')#, origin='lower') # inferno - good
	#~ cbar = plt.colorbar()
	#~ cbar.ax.set_ylabel('Counts')
	#~ plt.show()


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

	return popt[1], popt[2]


def photon_events(data,cts_5sig):
	# Using the cut-off counts in a pixel in data (cts_5ig), create a new 2D array that:
	#			0 - counts in pixel < cts_5sig
	#			1 - counts in pixel >= cts_5sig
	# Return this array at the end of the function
	#
	#
	events = numpy.zeros( shape=numpy.shape(data) )
	events[numpy.where( (data >= cts_5sig) & (data < 30000) )] += 1
	print "Total counts from events: ", numpy.size(numpy.where( (data >= cts_5sig) ))

	# Plot the resulting 2D image to pick out a spectral line to collapse to 1d spectrum
	# plot the 2d histogram
	#~ fig = plt.figure()
	#~ ax1 = fig.add_subplot(1,1,1)
	#~ ax1.set_xlabel('x',weight='bold',size='x-large')
	#~ ax1.set_ylabel('y',weight='bold',size='x-large')
	#~ ax1.set_axis_bgcolor('black')
	#~ ax1.tick_params(labelsize=18)
	#~ #ax1.set_title('CLICK ON SPECTRAL LINE TO ANALYZE')


	#~ plt.imshow(events, norm=LogNorm(vmin=0.001, vmax=1), cmap='inferno')#, origin='lower') # inferno - good
	#~ cbar = plt.colorbar()
	#~ cbar.ax.set_ylabel('Counts')
	#~ plt.show()

	return events

# 1. If creating new file, do this part:
def write_newfits(file,events):
	# Using the new photon-counting array created by the 5-sig line fit,
	# open and write to a fits file
	try:
		hdu = fits.PrimaryHDU(events)
		#~ hdu.writeto(file)
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
	# First, read-in previous list of events
	try:
		hdulist=fits.open(file,mode='update')
		print hdulist.info()
		#~ events_prev = hdulist[0].data
		#~ events_prev= events_prev + events
		hdulist[0].data = hdulist[0].data + events
		mx=numpy.max(hdulist[0].data)
		print mx

		if (event_number % 10) == 0:
			# Plot to see that hdulist[0].data updated with new events
			fig = plt.figure()
			ax1 = fig.add_subplot(1,1,1)
			ax1.set_xlabel('x',weight='bold',size='x-large')
			ax1.set_ylabel('y',weight='bold',size='x-large')
			ax1.set_axis_bgcolor('black')
			ax1.tick_params(labelsize=18)
			#ax1.set_title('CLICK ON SPECTRAL LINE TO ANALYZE')

			plt.imshow(hdulist[0].data, norm=LogNorm(vmin=0.001, vmax=mx), cmap='viridis')#, origin='lower') # inferno - good
			cbar = plt.colorbar()
			cbar.ax.set_ylabel('Counts')
			plt.show()

		hdulist.flush()		# Should update file with new events array
		hdulist.close()
		print "Updating %s SUCCESS!" % (file)
		returncode=0
	except:
		print "Update to %s FAILED" % (file)
		returncode=1

	return returncode





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

# File location and name
directory = "C:\Users\User\Documents\FIREBall-2 python\\170831\\darks\\"   #"." #Directory to use
#~ directory = "C:\Users\User\Documents\FIREBall-2 python\\test_images\\"
filename_root = "image" #Substring to find in filenames
num0 = 0 #File number you want to start on
print num0
#filename = directory+"%s%06i.fits" % (filename_root,num0)
delay = 10 #Time to wait before moving on to next file

quit = False
i = 0
num = num0
# Define field #: 1 - 4, will determine target field and where spectrograph boxes must be placed
field = 1

#Other variables
now = datetime.now()
logfile = "filetrack_science_%02i%02i%02i_%02i%02i.log" % (now.year%100,now.month,now.day,now.hour,now.minute)
logfile_gauss = "filetrack_ccdparms_%02i%02i%02i_%02i%02i.log.txt" % (now.year%100,now.month,now.day,now.hour,now.minute)


#Modifications
directory = os.path.abspath(directory) #Make sure directory is absolute path
log(logfile,"Checking directory: %s" % (directory))
log(logfile,"File:     \t \t  Total Photon Events:")
log(logfile_gauss,"File:   \t  \t  \t  Gaussian Parameters: ")
log(logfile_gauss,"\t  \t  \t x0 (cts) \t stdev (cts) \t Gain \t")
log(logfile_gauss,"---------------- \t -------- \t ----------- \t ------\t")

#Keep running program unless something sets break condition (quit=True)
while not(quit):
	#Get filename for this image
	filename = "%s%06i.fits" % (filename_root,num)

	#Create booleans to keep track of whether each file is found
	filefound = False

	#Run through all files in directory and try to match names
	# THIS CHECK IS FOR IMAGES
	for f in os.listdir(directory):
		if filename in f: filefound=True

	# No fits file found with correct name.
	# Re-look for fits file after delay
	if not filefound:
		#Wait the given amount of time before moving on
		log(logfile,"FITS file not created/found yet.; Sleeping... %2i seconds" % (delay))
		time.sleep(delay)

	# IF fits file found with correct name, then open and do operations
	elif filefound:
		# Read in image file
		data = read_fits(os.path.join(directory,filename))
		print type(data)

		max=numpy.max(data)
		x_range = numpy.arange(0,max+1)
		y_range = numpy.zeros( max+1 )
		print numpy.size(x_range), numpy.size(y_range)
		for i in numpy.ravel(data):
			y_range[i] += 1
		y_range2=numpy.log10(y_range)
		ymx = numpy.max(y_range2)
		for i in range(0, numpy.size(y_range2)):
			if  numpy.isnan(y_range2[i])=='True' or numpy.isinf(y_range2[i])=='True' :
				y_range2[i]=0
			elif  y_range2[i]==float('-inf') or y_range2[i]==float('inf'):
				y_range2[i]=0

		x_range_gauss =numpy.arange(numpy.where(y_range2==ymx)[0] -500, numpy.where(y_range2==ymx)[0] +500)
		y_range_gauss = y_range2[x_range_gauss]


		# YES!
		plt.plot(x_range,y_range2,drawstyle='steps-mid')
		plt.plot(x_range_gauss, y_range_gauss, drawstyle='steps-mid',color='r')
		x0, sig = gaus(x_range_gauss, y_range_gauss)
		plt.xlim(0,max)
		#~ plt.xlim(10000,20000)
		plt.ylim(0,numpy.max(y_range2))
		plt.title(filename)


		# For now, set stdv = num.size(x)/6.
		stdv = sig*5 	#num.size(x_range_gauss)/6.
		print stdv
		photon_list = photon_events(data,stdv+x0)
		lin_start = numpy.fix(stdv+numpy.median(x_range_gauss))			# Start 5-sigma away from read-out Gaussian shape
		lin_start = numpy.int_(lin_start)
		lin_end = lin_start+1000

		lnfit = numpy.polyfit(x_range[lin_start:lin_end],y_range2[lin_start:lin_end],1)
		yfit = map(lambda x: lnfit[0]*x + lnfit[1], x_range[lin_start:])
		yfit=numpy.array(yfit)
		endln = x_range[numpy.where(yfit<0)[0]+lin_start]
		endln = endln[0]
		print endln

		gain = (-1./lnfit[0])
		print lnfit
		print 'Determined gain: ',gain
		log(logfile_gauss,'%s \t %0.2i \t \t %0.2f \t %05i' % (filename, x0, sig, gain))

		print 'Total counts in raw data: ',numpy.sum(10**(y_range2[lin_start:endln]))
		ysum = numpy.sum(10**(y_range2[lin_start:endln]))
		print 'Total counts from line fit:',numpy.sum(10**yfit[0:endln-lin_start])
		log(logfile,"%s \t \t %06i" % (filename, ysum))

		# Store new events data array into its own fits file for later use
		# ALSO, chances are that events.fits already exists, so we want to write two files:
		# 1. Write to events+%06i.fits % num
		# 2. Read in events_fieldxx.fits
		# 3. Events_update = events_previous + events_current
		# 4. Write new Events_update to evets_fieldxx.fits
		# Only write events to events+num.fits and events_fieldxx.fits
		file1 = "events%06i.fits" % (num)
		file1 = os.path.join(directory,file1)
		file2 = "events_field%02i.fits" % (field)
		file2 = os.path.join(directory,file2)
		if num == num0:		# Special case: first file, so no events file exist yet
			#~ returncode = write_newfits(file1,photon_list)
			#~ print returncode
			returncode = write_newfits(file2,photon_list)
			print returncode
		else:		# All other cases: events have been recorded
			#~ returncode = write_newfits(file1,photon_list)
			#~ print returncode
			returncode = write_fits(file2,photon_list,num)


		plt.plot(x_range[lin_start:],y_range2[lin_start:],drawstyle='steps-mid',color='y')
		# overplot line fit
		plt.plot(x_range[lin_start:],yfit,linestyle='dashed',color='k')

		#~ plt.show(block=False)
		#~ plt.show()
		plt.savefig(os.path.join(directory,filename+'.png'),orientation='landscape')
		plt.clf()
		time.sleep(delay)
		print 'End of sleep'
		num+=1







