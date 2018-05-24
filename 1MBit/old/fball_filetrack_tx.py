#!/usr/bin/env python2

#
# Handles the compression of new image and houskeeping files
# on the DOBC during flight:
#			- Search for new image file (incremented by number)
#			- Compress new image file and existing housekeeping files (separately)
#			- Send each compressed file through the 1 MBit transmitter/receiver c-code
#			- increment +1 to image file count.
#

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
		#~ "hk": "housekeeping",
		#~ "img": "nuvuimages"
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
	delay = 10 # Seconds to wait before moving on to next file
	tarstring = ".tar.gz" # Tarball filename suffix
	program = "./test"		# Executable from test.c
	tar_cmd = "gzip" # Command used to tarball files
	tar_args = "-czf" # Arguments to use when tarballing

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
		dt = current - timeinit
		# Get filename for housekeeping
		hk_name = "housekeeping"
		hk_filepath = os.path.join(directories["hk"],hk_name)

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
		tarballfound = os.path.isfile(filepath + tarstring)

		# If both file and tarball exist - just move on to next file
		if filefound and tarballfound:
			log(logfile, "Image, compressed image, and compressed housekeeping exist for %s -- Moving to next image." % filename)
			filenum += 1
			time.sleep(1)		# Just delay a second before continuing
			##dt = current - timeinit

		# If file exists but no tarball, make tarball
		elif filefound and not tarballfound:
			log(logfile, "Compressing to file: %s" % (filename+tarstring))
			returncode = tar_image(filename, directories["img"], tarstring)
			if returncode != 0:
				log(logfile, "tar.add() [FITS image] command failed: %s %s %s" % (
					tar_cmd,
					tar_args,
					filepath
				))
				break

			# 1. Image tarball sent through transmitter
			filepath += tarstring
			log(logfile, "--> Sending %s to comm board" % (filepath))
			returncode = comm_command(program, filepath)
			if returncode != 0:
				log(logfile, "Error executing command: %s %s" % (program, filepath))
				break
			else:
				log(logfile, "%s successfully sent!" % (filepath))

			# Now, delay a short time to make sure receiver is cleared
			time.sleep(delay)

			# Tarball housekeeping data
			log(logfile, "Compressing to file: %s" % (hk_filepath + tarstring))
			returncode = tar_housekeeping(hk_name, directories["hk"], tarstring, housekeeping)
			if returncode != 0:
				log(logfile, "tar.add() [housekeeping] command failed: %s %s %s" % (
					tar_cmd,
					tar_args,
					filepath
				))
				break

			# 2. Housekeeping tarball send through transmitter
			hk_filepath += tarstring
			log(logfile, "--> Sending %s to comm board" % (hk_filepath))
			returncode = comm_command(program, hk_filepath)
			if returncode != 0:
				log(logfile, "Error executing command: %s %s" % (program, hk_filepath))
				break
			else:
				log(logfile, "%s successfully sent!" % (hk_filepath))

			# Again, delay a short time to make sure receiver has time to cleared
			time.sleep(delay)

			filenum += 1
			log(logfile, "Next image number looking for: %06i" % (filenum))
			#~ #Wait the given amount of time before moving on
			#~ # Actually, don't wait --> continue to next, if available
			time.sleep(delay)

		#If no file or tarball exist, probably just not created yet. Just wait.
		elif not filefound and not tarballfound:
			# Wait the given amount of time before moving on
			log(logfile, "FITS file not created/found yet.")
			log(logfile, "Sleeping... %2i seconds" % (delay))

			# Still send down
			time.sleep(delay)

		# If tarball exists but no file. This is always an error.
		else:
			log(logfile, "WARNING: Tarball found for %s but no raw image." % filepath)
			break



# Wrap print+file output together
def log(logfile, string):
	print(string)
	with open(logfile, 'a') as f:
		f.write(string + '\n')

def tar_image(file, path, compression):
	print file
	filepath = os.path.join(path, file)
	if os.name == "posix":		# linux: use Popen for command line tarball
		tar = filepath+compression
		try:
			p=subprocess.call(["tar","-czf",tar,filepath])
			returncode = 0
		except:
			print "subprocess.call() did not work for %s tar" % (tar)
			returncode = 1
	# Open image tarfile with tarfile
	elif os.name == "nt": # windows: use built-in tarfile command in python
		tar = tarfile.open(filepath+compression, 'w:gz')
		print filepath+compression
		try:
			tar.add(os.path.join(path,file),arcname=file)
			returncode = 0
		except:
			returncode = 1
		tar.close()
	return returncode


def tar_housekeeping(file, path, compression, files):
	filepath = os.path.join(path, file)
	if os.name == "posix":		# linux: use Popen for command line tarball
		tar = filepath+compression
		try:
			p=subprocess.call(["tar","-czf",tar,filepath+files])
			returncode = 0
		except:
			print "subprocess.call() did not work for %s tar" % (tar)
			returncode = 1
	elif os.name == "nt": # windows: use built-in tarfile command in python
		tar = tarfile.open(filepath + compression, 'w:gz')
		try:
			for name in files:
				tar.add(os.path.join(path, name),arcname=name)
			returncode = 0
		except:
			returncode = 1
		tar.close()
	return returncode


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
