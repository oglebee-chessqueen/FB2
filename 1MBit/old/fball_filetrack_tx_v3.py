# MUST be run through virtualenv!:
#
# snape:/home/fireball2/Documents/Communications/comsync-r15/python_env/bin/python
# (or in the folder: python_env/bin/python )
#
#
#
# Handles the compression of new image and houskeeping files
# on the DOBC during flight:
#			- Search for new image file (incremented by number)
#			- Compress new image file and existing housekeeping files (separately)
#			- Send each compressed file through the 1 MBit transmitter/receiver c-code
#			- increment +1 to image file count.
#
##
### MAJOR CHANGES:
##
#		- Files no longer compressed - send down as-is
#		- FITS files --> Converted to TXT files (including header info)
#

import os
import subprocess
import sys
import tarfile
import time
from datetime import datetime
from astropy.io import fits
import numpy
import shutil


def main():
	if os.name == "posix":
		root = "/home/fireball2"
		dir = '/'
	elif os.name == "nt": # windows
		root = "C:\\Users\\User\\Documents\\FIREBall-2 python\\"
		dir = '\\'
	else:
		print "Unrecognized platform, exiting."
		exit(1)

	directories = {
		"hk": "data/170929",
		"img": "data/170929"
	}

	for key, value in directories.iteritems():
		directories[key] = os.path.normpath(os.path.join(root, value))+dir

	filename_root = "image" # Substring to find in filenames
	filenum0 = 0 # File number you want to start on
	# Housekeeping names not expected to change
	housekeeping = [
		"alltemps.csv",
		"power.csv",
		"discretecom.csv",
		"waterpress.csv",
	]
	delay = 10 # Seconds to wait before moving on to next file
	program = "./test"		# Executable from test.c


	#Other variables
	timeinit = datetime.now()
	logfile = "filetrack_tx_%02i%02i%02i_%02i%02i.log" % (
		timeinit.year % 100,
		timeinit.month,
		timeinit.day,
		timeinit.hour,
		timeinit.minute
	)
	filenum = filenum0

	#Keep running program unless something sets break condition
	while True:
		# Log the start time
		current = datetime.now()

		log(logfile, "\nTime: %02i%02i%02i_%02i:%02i:%02i" % (
			current.year%100,
			current.month,
			current.day,
			current.hour,
			current.minute,
			current.second
		))

		# Get filename for this image
		filename = "%s%06i.fits" % (filename_root, filenum)
		filepath = os.path.join(directories["img"], filename)

		log(logfile, "File: %s" % filename)

		# Keep track of whether each file is found
		filefound = os.path.isfile(filepath)

		# If file exists:
		if filefound:
			# 1a. Create a copy of image.fits in backup drives
			returncode = backup_fits(directories["img"], filename)
			if returncode != 0:
				log(logfile,"Copy of %s FAILED --> continuing..." % (filename))
			else:
				log(logfile,"%s Copied to USB Drives!" % (filename))

			# 1. Read in FITS image, same header and 2D image array to a txt file.
			rtncode, new_filepath = read_fits(filepath, logfile)
			if rtncode != 0:
				log(logfile, "ERROR: Converting FITS to TXT for %s FAILED" % (filepath))
				break
			else:
				log(logfile, "--> Sending %s to comm board" % (new_filepath))

			# 2. Send image file through transmitter
			returncode = comm_command(program, new_filepath)
			if returncode != 0:
				log(logfile, "Error executing command: %s %s" % (program, new_filepath))
				break
			else:
				log(logfile, "%s successfully sent!" % (new_filepath))

			# Now, delay a short time to make sure receiver is cleared
			time.sleep(delay)
			filenum += 1


			# 2. Housekeeping tarball send through transmitter
			for hk in housekeeping:
				hkfile = os.path.join(directories["hk"],hk)
				log(logfile, "--> Sending %s to comm board" % (hkfile))
				returncode = comm_command(program, hkfile)
				if returncode != 0:
					log(logfile, "Error executing command: %s %s" % (program, hkfile))
					break
				else:
					log(logfile, "%s successfully sent!" % (hkfile))

				# Again, delay a short time to make sure receiver has time to cleared
				time.sleep(delay)

			log(logfile, "Next image number looking for: %06i" % (filenum))
			time.sleep(delay)		# Add delay to allow for Rx PURGE time

		#If no file or tarball exist, probably just not created yet. Just wait.
		elif not filefound:
			# Wait the given amount of time before moving on
			log(logfile, "FITS file not created/found yet.")
			log(logfile, "Sleeping... %2i seconds" % (delay))

			# Still send down
			time.sleep(delay)

		# If tarball exists but no file. This is always an error.
		else:
			log(logfile, "SOMETHING IS WRONG -- BREAKING." % filepath)
			break





# Wrap print+file output together
def log(logfile, string):
	print(string)
	with open(logfile, 'a') as f:
		f.write(string + '\n')





def read_fits(filename,logfile):
	new_file = filename+".txt"	# New file extension
	ymin = 70
	ymax = 2000
	xmin = 1000
	xmax = 2150

	try:
		# Open fits with astropy
		hdulist = fits.open(filename)
		# CHANGE TO CORRECT CALLABLE ONCE KNOWN
		hrd = hdulist[0].header		# Can do hdr.comments[' '] to check header comments
		data = hdulist[0].data
		data = data[ymin:ymax,xmin:xmax]
		data = data - mindata
		data = numpy.int_(data)
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
			outfile.write('# Header info: %s \t %s \t %03i \t %04i \t %.2f \t %s \n' % (h1,h2,h3,h4,h5,h9))
			outfile.write('# MIN: \n' )
			outfile.write('# %05i \n' % (mindata))
			outfile.write('# \t %05i \n' % (mindata))
			outfile.write('# \t \t %05i \n' % (mindata))
			numpy.savetxt(outfile, data, fmt='%i')#, fmt='%.4f')
		returncode = 0
	except:
		returncode = 1

	return returncode, new_file





# Method for running comm C-executable to transmit tar files to ground
def comm_command(program, tar_file):
	if os.name == "posix":		# linux: run ./test for transmission
		read, write = os.pipe()
		# IF Transmit:
		os.write(write, "y\n y\n y\n 11\n 256\n 1\n 2\n %s\n y\n 14\n" % (tar_file))
		os.close(write)
		try:
			p=subprocess.check_call([program],stdin=read)
			returncode = 0
		except:
			returncode = 1
	elif os.name == "nt": # windows: ./test won't run, so just skip
		print "Running transmittion code (Win: simulated): %s" % (tar_file)
		time.sleep(10)
		returncode = 0
	return returncode



def backup_fits(origPath, filename):
	'''
	Use to back up image fits files to USB drives in:
	/home/fireball2/databackup0
	/home/fireball2/databackup1
	'''
	origFile = os.path.join(origPath, filename)
	destPath1 = "/home/fireball2/databackup0"
	destPath2 = "/home/fireball2/databackup1"
	if os.name == "posix":		# linux: run ./test for transmission
		try:		# Move to USB 1, then 2
			newfile1 = os.path.join(destPath1, filename)
			subprocess.Popen(["cp", "-v", origFile, newfile1])
			newfile2 = os.path.join(destPath2, filename)
			subprocess.Popen(["cp", "-v", origFile, newfile2])
			returncode = 0
		except:
			print "Copy to USB Drive FAILED - Continue"
			returncode = 1
	else:
		print "Not Linux -- continue"
		returncode = 1

	return returncode



if __name__ == "__main__":
	main()
