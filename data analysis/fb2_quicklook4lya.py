'''
	FB2 -- F2 FLIGHT DATA
	---------------------
	Co-add spots where LyA emission is expected.
		- Read in LyA mask positions (Vincent's reg files)
		- Collapse spectra in vertical direction
		- Co-add collapsed spectra together, assuming LyA center is te center of each box
		- See if any signal builds up; if so, try to fit a Gaussian to it
	Other things to do afterwards  if improvements are needed:
		- Do a full background subtraction on full science image;
			Gillian did it per image and co-added for the final image, this time
			do the same operation but on the final image.
		- Read in Zinc lamp lines reg file to determine wavelength solution
			per slit
				- Also read in redshifts of each galaxy and correct the wavelength
				  solution to reflect rest frame of the galaxies
				- Co-add around where LyA emission is expected.
		- Talk to Donal about where he would expect to see LyA emission from CGM
			(peaked at LyA center? blue-shifted? red-shifted?)
'''

def read_fits(fitsfile):
	'''
	Read in the FITS file.
	Save to a numpy array, return to main program.
	'''
	from astropy.io import fits

	hdulist = fits.open(fitsfile)
	hrd = hdulist[0].header
	data = hdulist[0].data		# shape = [2069, 1080] (should already be a numpy array)
	data[data>12500] = 0

	return data

# To plot the image
def plot_image(data,x,y,dx,dy,label,x_spec):
	fig = plt.figure(figsize=(10,15))
	ax1 = fig.add_subplot(1,1,1)
	ax1.set_xlabel('x',weight='bold',size='x-large')
	ax1.set_ylabel('y',weight='bold',size='x-large')
	ax1.set_facecolor ('black')
	ax1.tick_params(labelsize=18)
	plt.imshow(data, vmin=-5000, vmax=15000, cmap='viridis', origin='lower') # inferno - good
	cbar = plt.colorbar()
	cbar.ax.set_ylabel('Counts',size='x-large')
	#~ cbar.tick_params(labelsize=18)

	# Makes boxes
	for k in range(0,len(x)):
		ax1.add_patch(
					 patches.Rectangle(
					 (x[k], y[k]),
					 dx[k],
					 dy[k],
					 fill=False ,     # remove background
					 edgecolor='red'
					)
		)
		plt.text(x[k]+dx[k], y[k]+dy[k], '%s' % label[k], color='red')

	for k in range(0,len(x)):
		ax1.add_patch(
					 patches.Rectangle(
					 (x[k]-(x_spec/2), y[k]),
					 dx[k]+x_spec,
					 dy[k],
					 fill=False ,     # remove background
					 edgecolor='yellow'
					)
		)


	plt.savefig("test_image_GALEXbright.png")
	plt.clf()

	return


def make_spectrum(spec):
	'''
	Collapse the given 2D array along the y-axis, to create a 1D spectrum.
	'''
	return numpy.sum(spec,axis=0)



'''
	MAIN PROGRAM
'''
if __name__ == "__main__":
	import numpy
	import scipy
	import matplotlib.pyplot as plt
	from matplotlib.colors import LogNorm
	import matplotlib.patches as patches

	#~ imagefile = "/home/keri/fb2/image_65_146.sum.fits"	# Co-added image file
	imagefile = "/home/keri/fb2/polyfit_redux/image_65_146.sum.fits"	# LyA region file
	regfile = "/home/keri/fb2/F2_-161_Lya-crop_v2.reg"	# LyA region file
	regfile = "/home/keri/fb2/F2_-161_Zn_Lya-crop_v2.reg"	# LyA region file


	# Define arrays to store values out of region file
	# (defines box around LyA features in x,y,dx,dy pixels on detector)
	x = []
	y = []
	dx = []
	dy = []
	label = []	# Label of the LyA slit; makes sure we don't include OVI, LyC, others
	x_extent = 1000		# extra pixels to collapse to make spectra

	# Open region file, extract label + box coordinates/widths
	with open(regfile) as ff:
		for line in ff:
			if line.startswith("box"):
				row = line.split()
				# for label text
				#~ print row
				# If there are not 4 elements in the rows, then exit because have recorded all the slits
				try:
					text = row[3]
				except:
					break
				try:
					if text[6:-2] == 'GALEXbright':
						label.append( text[6:-1] )
						#~ print "Found a bright Galaxy"
					else:
						continue
					#~ label = int(text[6:-1])
					#~ print label
				except:
					print "Label not LyA location: continue"
					continue #want to continue onto next line --> yes, works
				tmp = row[0]
				tmp2 = tmp[4:-1]
				# find where first comma appears
				pos = tmp2.find(',')
				#~ print tmp2, pos
				# save to x array
				x.append( float(tmp2[0:pos]) )
				#~ x = tmp2[0:pos]

				# Take out from tmp2 to find next index
				tmp2 = tmp2[pos+1:]
				#~ print x, tmp2
				# Repeat
				pos = tmp2.find(',')
				#~ print tmp2, pos
				# save to x array
				y.append( float(tmp2[0:pos]) )
				#~ y = tmp2[0:pos]
				# Take out from tmp2 to find next index
				tmp2 = tmp2[pos+1:]
				#~ print y, tmp2

				# Repeat
				pos = tmp2.find(',')
				#~ print tmp2, pos
				# save to x array
				dx.append( int(tmp2[0:pos]) )
				#~ dx = tmp2[0:pos]
				# Take out from tmp2 to find next index
				tmp2 = tmp2[pos+1:]
				#~ print dx, tmp2

				# Repeat
				pos = tmp2.find(',')
				#~ print tmp2, pos
				# save to x array
				dy.append( int(tmp2[0:pos]) )
				#~ y = tmp2[0:pos]
				# Take out from tmp2 to find next index
				tmp2 = tmp2[pos+1:]
				#~ print dy, tmp2

				#~ print

	#~ print label
	#~ print x
	#~ print y
	#~ print dx
	#~ print dy
	# I think x,y are flipped?


	# Read in FITS file, save image.
	data = read_fits(imagefile)


	# Verify with Gillian how the boxes are made:
	# -Is it that x,y are one corner of the box, and you add dx, dy to them to make the box?
	# -Is x,y the center, and you have to do x +/- dx/2, y +/- dy/2?


	# Plot image, make boxes on image where LyA should be
	plot_image(data,x,y,dx,dy,label,x_extent)
	# Makes boxes
	#~ for k in range(0,len(x)):
		#~ ax1.add_patch(
					 #~ patches.Rectangle(
					 #~ (y[k], x[k]),
					 #~ dy[k],
					 #~ dx[k],
					 #~ fill=False ,     # remove background
					 #~ edgecolor='red'
					#~ )
		#~ )
		#~ plt.text(y[k]+dy[k], x[k]+dx[k], 's' % label[k], color='red')

	# collapse spectrum into 1D
	for i in range(0,len(label)):
		#~ print x[i], int( x[i] )
		xmin = int(x[i])-(x_extent/2)
		if xmin < 0:
			xmin = 0
		xmax = int(x[i])+dx[i]+(x_extent/2)
		if xmax > numpy.size(data[:,0]):
			xmax = numpy.size(data[:,0])
		ymin = int(y[i])#-5
		ymax = int(y[i])+dy[i]
		#~ print xmin, xmax, ymin, ymax

		imgbox = data[xmin:xmax,ymin:ymax]
		imgbox = data[ymin:ymax,xmin:xmax]
		spectrum = make_spectrum(imgbox)
		# plot to make sure this looks right
		#~ print len(spectrum)
		# binning option: define bin length, then x-axis values
		bin = 6
		# make x-axis:
		xx = numpy.arange(0,len(spectrum),bin)
		#~ print xx

		spec_bin = numpy.zeros( len(xx) )
		for k in range(0,len(spectrum),bin):
			spec_bin[k/bin] = numpy.mean(spectrum[k:k+bin])#/bin
			#~ print k/bin
		#~ print spec_bin

		plt.plot(spectrum,drawstyle='steps-mid')
		plt.plot(xx,spec_bin,drawstyle='steps-mid',color='k',lw=5)
		plt.savefig("test_spec_GALEXbright%i.png"%(i+1))
		plt.clf()




