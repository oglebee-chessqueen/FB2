

def read_fits(filename):
	new_file = filename+".txt"	# New file extension
	ymin = 70
	ymax = 2000
	xmin = 1000
	xmax = 2150

	# Open fits with astropy
	hdulist = fits.open(filename)
	# CHANGE TO CORRECT CALLABLE ONCE KNOWN
	hrd = hdulist[0].header		# Can do hdr.comments[' '] to check header comments
	data = hdulist[0].data
	data = numpy.int_(data)
	subdata = data[ymin:ymax,xmin:xmax]
	mindata = numpy.min(subdata)
	print numpy.where(data[ymin:ymax,xmin:xmax] == mindata)
	print data[ymin+1576,xmin+25]


	fig = plt.figure()
	ax1 = fig.add_subplot(1,1,1)
	ax1.set_xlabel('x',weight='bold',size='x-large')
	ax1.set_ylabel('y',weight='bold',size='x-large')
	ax1.set_axis_bgcolor('black')
	ax1.tick_params(labelsize=12)
	plt.imshow(data, norm=LogNorm(vmin=15000, vmax=20000), cmap='viridis')#, origin='lower') # inferno - good
	cbar = plt.colorbar()
	cbar.ax.set_ylabel('Counts')


	print mindata #numpy.shape(data)
	data = data[ymin:ymax,xmin:xmax]
	data = data - mindata
	print numpy.min(data[ymin:ymax,xmin:xmax])
	print numpy.where(data[ymin:ymax,xmin:xmax] == numpy.min(data[ymin:ymax,xmin:xmax]))
	print data[1576,25], data[1785,73]

	data = numpy.int_(data)
	print numpy.shape(data)
	plt.show()
	h1 = hrd['DATE'] # %s - YYYY-MM-DDThh:mm:ss UT <--
	h2 = hrd['IMG'] # %s  <--
	h3 = hrd['EXPTIME'] # %03i  <--
	h4 = hrd['EMGAIN'] # %04i <--
	h5 = hrd['PREAMP'] # %.2f  <--
	h6 = hrd['IMNO'] # %03i
	h7 = hrd['IMBURST'] # %01i
	h8 = hrd['SHUTTER'] # %01i
	h9 = hrd['TEMP'] # %s  <--
	hdulist.close()

	# Write the array to disk
	with file(new_file, 'w') as outfile:
		print "Writing to new file: %s" % (new_file)
		print hrd
		outfile.write('# Header info: %s \t %s \t %03i \t %04i \t %.2f \t %s \n' % (h1,h2,h3,h4,h5,h9))
		outfile.write('# MIN: \n' )
		outfile.write('# %05i \n' % (mindata))
		outfile.write('# \t %05i \n' % (mindata))
		outfile.write('# \t \t %05i \n' % (mindata))
		numpy.savetxt(outfile, data, fmt='%i')#, fmt='%.4f')
	returncode = 0


	return returncode, new_file



if __name__ == "__main__":
	import os
	import subprocess
	import sys
	import tarfile
	import time
	from datetime import datetime
	from astropy.io import fits
	import numpy
	import matplotlib.pyplot as plt
	from matplotlib.colors import LogNorm


	#~ directory = "C:\Users\\Keri Hoadley\\Documents\\FIREBall-2\\python\\FIREBall-2 python\\170901_darks\\focus\\"   #"." #Directory to use
	directory = "C:\Users\\Keri Hoadley\\Documents\\FIREBall-2\\python"
	#~ directory = "C:\Users\User\Documents\FIREBall-2 python\\test_images\\"
	filename_root = "image" #Substring to find in filenames
	num0 = 0
	for i in range(num0,1):
		filename = "%s%06i.fits" % (filename_root,i)
		rc, new_file = read_fits(os.path.join(directory,filename))

		new_data = numpy.loadtxt(new_file)
		print new_data.shape
		new_data=new_data*1.0E+4

		fig = plt.figure()
		ax1 = fig.add_subplot(1,1,1)
		ax1.set_xlabel('x',weight='bold',size='x-large')
		ax1.set_ylabel('y',weight='bold',size='x-large')
		ax1.set_axis_bgcolor('black')
		ax1.tick_params(labelsize=18)
		plt.imshow(new_data, norm=LogNorm(vmin=15000, vmax=20000), cmap='viridis')#, origin='lower') # inferno - good
		cbar = plt.colorbar()
		cbar.ax.set_ylabel('Counts')
		plt.show()



