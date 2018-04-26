##
##
## QUICKLOOK of FIREBall-2 Images:
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
import socket
#~ import pickle




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
		"img": "",
	}
	for key, value in directories.iteritems():
		directories[key] = os.path.normpath(os.path.join(root, value))+dir
	# File location and name
	filename_root_image = "image"		#Substring to find in filenames
	if len(sys.argv) == 2:
		print "Arguments called: ", sys.argv[1]
		num0 = int(sys.argv[1])
	else:
		num0 = 0			# IMAGE File number you want to start on
	print "Initial starting number: ", num0

	#Other variables
	now = datetime.now()
	quit = False
	#~ i = 0
	num = num0
	delay = 10 			#Time to wait before moving on to next file


	# Log progress of quicklook script
	logfile = "log_FB2Quicklook1_%02i%02i%02i_%02i%02i.log" % (now.year%100,now.month,now.day,now.hour,now.minute)
	log(logfile,"Checking directory: %s" % (directories["img"]+datetime.now().strftime("%y%m%d")))

	#Keep running program unless something sets break condition (quit=True)
	while not(quit):
		#~ for key, value in directories.iteritems():
			#~ directories[key] = os.path.join(value, datetime.now().strftime("%y%m%d"))
			#~ print directories[key]
		filename = "%s%06i.txt" % (filename_root_image,num)			# If events_fieldsxx.fits

		#Create booleans to keep track of whether each file is found
		filefound = False

		#Run through all files in directory and try to match names
		# THIS CHECK IS FOR IMAGES
		for f in os.listdir(directories["img"]+datetime.now().strftime("%y%m%d")):
			if filename in f: filefound=True

		# No fits file found with correct name.
		# Re-look for fits file after delay
		if not filefound:
			log(logfile,"File %s not found; sleeping..." % (filename))
			time.sleep(delay)

		# IF fits file found with correct name, then open and do operations
		elif filefound:
			# Read in image file
			log(logfile,"Current file: %s" % (filename))
			data = read_fits(os.path.join(directories["img"]+datetime.now().strftime("%y%m%d"),filename),logfile)
			log(logfile,"File: %s read in SUCCESSFULLY" % (filename))

			max=numpy.max(data)
			x_range = numpy.arange(0,max+1,1)
			y_range = numpy.zeros( numpy.size(x_range ) )

			for i in numpy.ravel(data):
				y_range[int(i)] += 1
			y_range2=numpy.log10(y_range)
			ymx = numpy.max(y_range2[1:])


			for i in range(0, numpy.size(y_range2)):
				if  numpy.isnan(y_range2[i])=='True' or numpy.isinf(y_range2[i])=='True' :
					y_range2[i]=0
				elif  y_range2[i]==float('-inf') or y_range2[i]==float('inf'):
					y_range2[i]=0


			x_range_gauss =numpy.arange(numpy.where(y_range2==ymx)[0] -500, numpy.where(y_range2==ymx)[0] +500)
			y_range_gauss = y_range2[x_range_gauss]


			# YES!
			peak, x0, sig = gaus(x_range_gauss, y_range_gauss)
			log(logfile,"Center of Read Noise = %.2f; Standard deviation = %.2f..." % (x0,sig))


			# For now, set stdv = num.size(x)/6.
			stdv = sig*5 	#num.size(x_range_gauss)/6.
			photon_list = photon_events(data,stdv+x0,os.path.join(directories["img"]+datetime.now().strftime("%y%m%d"),filename))

			lin_start = numpy.fix(stdv+numpy.median(x_range_gauss))			# Start 5-sigma away from read-out Gaussian shape
			lin_start = numpy.int_(lin_start)
			lin_end = lin_start+1000

			lnfit = numpy.polyfit(x_range[lin_start:lin_end],y_range2[lin_start:lin_end],1)
			yfit = map(lambda x: lnfit[0]*x + lnfit[1], x_range[lin_start:])
			yfit=numpy.array(yfit)

			fig = plt.figure()	#plt.gcf()
			#~ fig.set_size_inches(10.5, 8.5)
			ax1 = fig.add_subplot(1,1,1)
			ax1.set_xlabel('Cts Recorded in Pixels',weight='bold',size='large')
			ax1.set_ylabel('Total # of cts instances',weight='bold',size='large')
			ax1.tick_params(labelsize=12)
			ax1.set_title(filename[-10:-4])

			plt.plot(x_range,y_range2,drawstyle='steps-mid')		# Data
			plt.plot(x_range_gauss, y_range_gauss, drawstyle='steps-mid',color='r')		# Readnoise
			plt.xlim(10000,30000)
			plt.ylim(0,numpy.max(y_range2))
			plt.plot(x_range[lin_start:],y_range2[lin_start:],drawstyle='steps-mid',color='y')
			# overplot line fit
			plt.plot(x_range[lin_start:],yfit,linestyle='dashed',color='k')
			#~ plt.show()
			plt.savefig(os.path.join(directories["img"]+datetime.now().strftime("%y%m%d"),filename+'_HISTOGRAM.eps'),dvi=300,format='eps',orientation='landscape')
			plt.show()


			# Check that this worked?
			log(logfile,"Checked image and photon events in: %s; sleeping..." % (filename))
			#~ time.sleep(delay)
			print "End sleep..."
			num+=1






# Wrap print+file output together
def log(logfile, string):
	print(string)
	with open(logfile, 'a') as f:
		f.write(string + '\n')





def read_fits(filename, logfile):
	# Open fits with astropy
	img = numpy.zeros( shape=[2069,3216] )
	if filename.endswith('.fits'):
		hdulist = fits.open(filename,skip_header=2)
		hdulist.info()
		data = hdulist[0].data
		hrd = hdulist[0].header		# Can do hdr.comments[' '] to check header comments
		hdulist.close()
	# Else, if a text file, open with numpy.loadtxt
	elif filename.endswith(".txt"):
		# Define header captions here
		hrd_caps = ['DATE',
								'IMG',
								'EXPTIME',
								'EMGAIN',
								'PREAMP',
								'TEMP',
							]
		# Try to read in min value from file
		try:
			lines = open(filename).readlines()
			fields_headers = lines[0].split()
			hrds = fields_headers[3:]
			print hrds
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
		print min
		# Open with numpy load function
		cols = numpy.arange(0,1150)		# Define number of column in data
		data = numpy.genfromtxt(filename,comments="#",skip_header=5,usecols=cols,filling_values=(-1*min),invalid_raise=False)
		img[70:numpy.size(data[:,0])+70,1000:2150] = data + min
		print "Shape of the image from 1 Mbit file: ",numpy.shape(data)

		# Save output to a FITS file as "image000xxx.fits"
		# Take FITS headers (if available) from first line of txt files
		new_fits = filename[0:-4]+'.fits'
		try:
			# 1. Create header
			hdu = fits.PrimaryHDU()
			for i in range(0,len(hrd_caps)):
				hdu.header[hrd_caps[i]] = hrds[i]
				print hrd_caps[i], hdu.header[hrd_caps[i]]
			hdu.data = img
			hdu.writeto(new_fits)
			print "Creating %s SUCCESS!" % (new_fits)
		except:
			# If writing a new file failed:
			print "Creating %s FAILED" % (new_fits)



	fig = plt.figure()	#plt.gcf()
	fig.set_size_inches(10.5, 8.5)
	ax1 = fig.add_subplot(1,1,1)
	ax1.set_xlabel('x',weight='bold',size='large')
	ax1.set_ylabel('y',weight='bold',size='large')
	ax1.set_axis_bgcolor('black')
	ax1.tick_params(labelsize=12)
	ax1.set_title(filename[-10:-4])

	#~ data = numpy.fliplr(data)
	#~ plt.imshow(data, norm=LogNorm(vmin=data.min(), vmax=data.max()), cmap='viridis', origin='upper') # inferno - good    [:,xrange[0]:xrange[1]]
	plt.imshow(img, norm=LogNorm(vmin=10000, vmax=numpy.max(img)), cmap='viridis')#, origin='lower') # inferno - good
	#~ cbar = plt.colorbar()
	#~ cbar.ax.set_ylabel('Counts')
	plt.savefig(filename[0:-4]+'_RAW.eps', dpi=300, format='eps', orientation='landscape')
	#~ plt.show()


	return img



def gaus(x, y):
	'''
	Make a 1-D Gaussian fit to model the detector read noise and peaks in x-scan.
	'''
	# Initialize theta parameters
	theta_init = [numpy.max(y), numpy.max(x), numpy.size(x)/4.]
	print theta_init

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
		popt = numpy.array( theta_init )
		pcov = numpy.array( [[0,0,0],[0,0,0],[0,0,0]] )
		pass

	return popt




def photon_events(data,cts_5sig,filename):
	'''
	Using the cut-off counts in a pixel in data (cts_5ig), create a new 2D array that:
			0 - counts in pixel < cts_5sig
			1 - counts in pixel >= cts_5sig
	'''
	events = numpy.zeros( shape=numpy.shape(data) )
	events[numpy.where( (data >= cts_5sig) & (data < 30000) )] += 1
	print "Total counts from events: ", numpy.size(numpy.where( (data >= cts_5sig) ))

	fig2 = plt.figure()	#plt.gc
	fig2.set_size_inches(10.5, 8.5)
	ax1 = fig2.add_subplot(1,1,1)
	ax1.set_xlabel('x',weight='bold',size='large')
	ax1.set_ylabel('y',weight='bold',size='large')
	ax1.set_axis_bgcolor('black')
	ax1.tick_params(labelsize=12)
	ax1.set_title('Events Registered:')

	#~ data = numpy.fliplr(data)
	plt.imshow(events, vmin=0, vmax=1, cmap='viridis', origin='upper') # inferno - good    [:,xrange[0]:xrange[1]]
	#~ plt.imshow(data, norm=LogNorm(vmin=15000, vmax=20000), cmap='viridis')#, origin='lower') # inferno - good
	#~ cbar = plt.colorbar()
	#~ cbar.ax.set_ylabel('Photon registered')
	plt.savefig(filename[0:-4]+'_PHOTONCOUNTS.eps', dpi=300, format='eps', orientation='landscape')
	#~ plt.show()

	return events
















######### MAIN PROGRAM #########
if __name__ == "__main__":
	main()