#!/usr/bin/env python2

#
# Handles the compression of new image and houskeeping files
# on the DOBC during flight:
#			- Search for new image file (incremented by number)
#			- Compress new image file and existing housekeeping files (separately)
#			- Send each compressed file through the 1 MBit transmitter/receiver c-code
#			- increment +1 to image file count.
#
##
### MAJOR CHANGE:
##
#		- Files no longer compressed - send down as-is

import os
import subprocess
import sys
import tarfile
import time
from datetime import datetime


def main():
	if os.name == "posix":
		root = "/home/fireball2"#/Documents/Communications/comsync-r15"
		dir = '/'
	elif os.name == "nt": # windows
		root = "C:\\Users\\User\\Documents\\FIREBall-2 python\\"
		dir = '\\'
	else:
		print "Unrecognized platform, exiting."
		exit(1)

	directories = {
		#~ "hk": "data/170923",
		#~ "img": "data/170923/calibs"
		"hk": "data/170901",
		"img": "data/170901/calibs"
	}

	for key, value in directories.iteritems():
		directories[key] = os.path.normpath(os.path.join(root, value))+dir

	filename_root = "image" # Substring to find in filenames
	filenum0 = 0 # File number you want to start on
	# Housekeeping names not expected to change
	housekeeping = [
		"alltemps.csv",
		"nuvupressure.csv",
		"power.csv",
		"pressure.csv",
		#~ "dygraph-combined.js",
		#~ "index-fireball.html"
	]
	delay = 5 # Seconds to wait before moving on to next file
	program = "./test"		# Executable from test.c


	#Other variables
	timeinit = datetime.now()
	dt = 0		# Delta time from "now" to "current"
	logfile = "filetrack_tx_%02i%02i%02i_%02i%02i.log" % (
		timeinit.year % 100,
		timeinit.month,
		timeinit.day,
		timeinit.hour,
		timeinit.minute
	)
	i = 0
	filenum = filenum0

	#Keep running program unless something sets break condition
	while True:
		# Log the start time
		current = datetime.now()
		# Get filename for housekeeping
		#~ hk_name = "housekeeping"
		#~ hk_filepath = os.path.join(directories["hk"],hk_name)

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
		print filepath

		log(logfile, "File: %s" % filename)

		# Keep track of whether each file is found
		filefound = os.path.isfile(filepath)


		# If file exists:
		#~ if filefound:
		if all(map(os.path.isfile, filepath)):

			# 1. Image tarball sent through transmitter
			log(logfile, "--> Sending %s to comm board" % (filepath))
			returncode = comm_command(program, filepath)
			if returncode != 0:
				log(logfile, "Error executing command: %s %s" % (program, filepath))
				break
			else:
				log(logfile, "%s successfully sent!" % (filepath))

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
			#~ time.sleep(delay)

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




if __name__ == "__main__":
	main()
