#!/usr/bin/env python2

import os
import subprocess
import sys
import tarfile
import time
from datetime import datetime


def main():
	if os.name == "posix":
		root = "/home/user"
	elif os.name == "nt": # windows
		root = "C:\\Users\\User\\Documents"
	else:
		print "Unrecognized platform, exiting."
		exit(1)

	directories = {
		"obc": "FIREBall-2 python/170831/",
		"gnd": "FIREBall-2 python/170831_move_test/",
		"img": "FIREBall-2 python/170831/nuvutest/"
	}

	for key, value in directories.iteritems():
		directories[key] = os.path.normpath(os.path.join(root, value))

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
	logfile = "filetrack_%02i%02i%02i_%02i%02i.log" % (
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
		print dt
		hk_filepath = os.path.join(
			directories["obc"],
			"hk_%02i%02i%02i_%02i%02i%02i" % (
				current.year%100,
				current.month,
				current.day,
				current.hour,
				current.minute,
				current.second
			)
		)
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
		tarballfound = os.path.isfile(filepath + tarstring)

		# If both file and tarball exist - just move on to next file
		if filefound and tarballfound:
			log(logfile, "Image, compressed image, and compressed housekeeping exist for %s -- Moving to next image." % filename)
			filenum += 1
			##dt = current - timeinit

		# If file exists but no tarball, make tarball
		elif filefound and not tarballfound:
			log(logfile, "Compressing to file: %s" % (filepath + tarstring))
			returncode = tar_image(filepath, tarstring)
			if returncode != 0:
				log(logfile, "tar.add() [FITS image] command failed: %s %s %s" % (
					tar_cmd,
					tar_args,
					filepath
				))
				break

			# Do IF dt = 0 or dt % 60 = 0 (every minute or so)
			#~ if (dt==0) or (dt.seconds%60==0):		# Idea was to not do this for every image, but maybe do anyway?
			# Tarball housekeeping data
			hk_filepath = hk_filepath + "_%s%06i" % (filename_root, filenum)
			log(logfile, "Compressing to file: %s" % (hk_filepath + tarstring))
			returncode = tar_housekeeping(hk_filepath, directories["obc"], tarstring, housekeeping)
			if returncode != 0:
				log(logfile, "tar.add() [housekeeping] command failed: %s %s %s" % (
					tar_cmd,
					tar_args,
					filepath
				))
				break

			# Get filepath for new compressed file
			filepath += tarstring
			hk_filepath += tarstring

			# 1. Image tarball
			log(logfile, "--> Sending %s to comm board" % (filepath))
			returncode = comm_command(program, filepath)
			if returncode != 0:
				log(logfile, "Error executing command: %s %s" % (program, filepath))
				break
			else:
				log(logfile, "%s successfully sent!" % (filepath))

			# 2. Housekeeping tarball
			# Do IF dt = 0 or dt % 60 = 0 (every minute or so)
			#if (dt==0) or (dt.seconds%60==0):
			log(logfile, "--> Sending %s to comm board" % (hk_filepath))
			returncode = comm_command(program, hk_filepath)
			if returncode != 0:
				log(logfile, "Error executing command: %s %s" % (program, hk_filepath))
				break
			else:
				log(logfile, "%s successfully sent!" % (hk_filepath))

			filenum += 1
			log(logfile, "Next image number looking for: %06i" % (filenum))
			#~ #Wait the given amount of time before moving on
			#~ # Actually, don't wait --> continue to next, if available
			#~ time.sleep(delay)
			##dt = current - timeinit

		#If no file or tarball exist, probably just not created yet. Just wait.
		elif not filefound and not tarballfound:
			# Wait the given amount of time before moving on
			log(logfile, "FITS file not created/found yet.\nSleeping... %2i seconds" % (delay))

			# Still send back housekeeping data:
			if (dt == 0) or (dt.seconds % 60 < delay):
				log(logfile, "Compressing to file: %s" % (hk_filepath + tarstring))
				returncode = tar_housekeeping(hk_filepath, directories["obc"], tarstring, housekeeping)
				if returncode != 0:
					log(logfile, "tar.add() [housekeeping] command failed: %s %s %s" % (
						tar_cmd,
						tar_args,
						filepath
					))
					break

				hk_filepath += tarstring
				log(logfile, "--> Sending %s to comm board" % (hk_filepath))
				returncode = comm_command(program, hk_filepath)
				if returncode != 0:
					log(logfile, "Error executing command: %s %s" % (program, hk_filepath))
					break
				else:
					log(logfile, "%s successfully sent!" % (hk_filepath))

			# Still send down
			time.sleep(delay)
			##dt = current - timeinit

		# If tarball exists but no file. This is always an error.
		else:
			log(logfile, "WARNING: Tarball found for %s but no raw image." % filepath)
			break

		#~ log(logfile, "End time: %02i%02i%02i_%02i:%02i:%02i" % (
			#~ timeinit.year%100,
			#~ timeinit.month,
			#~ timeinit.day,
			#~ timeinit.hour,
			#~ timeinit.minute,
			#~ timeinit.second
		#~ ))


# Wrap print+file output together
def log(logfile, string):
	print(string)
	with open(logfile, 'a') as f:
		f.write(string + '\n')


def tar_image(file, compression):
	# Open image tarfile with tarfile
	tar = tarfile.open(file + compression, 'w:gz')
	try:
		tar.add(file)
		returncode = 0
	except:
		returncode = 1
	tar.close()
	return returncode


def tar_housekeeping(file, path, compression, files):
	tar = tarfile.open(file + compression, 'w:gz')
	try:
		for name in files:
			tar.add(os.path.join(path, name))
		returncode = 0
	except:
		returncode = 1
	tar.close()
	return returncode


def untar(file, destPath):
	tar = tarfile.open(file, 'r:gz')
	try:
		tar.extractall(path=destPath)
		returncode = 0
	except:
		#~ log(logfile, "tar.extractall() [%s] command failed" % (file))
		returncode = 1
	tar.close()
	return returncode


# Method for running comm C-executable to transmit tar files to ground
#~ def comm_command(program, tar_file):
	#~ return 0
	#~ returncode = subprocess.call([program, filepath])     # ????
	#~ return returncode

# Method for running comm C-executable to transmit tar files to ground
def comm_command(program, tar_file):
	return 0
	read, write = os.pipe()
	# IF Transmit:
	os.write(write, "y\n y\n y\n 9\n 11\n 256\n 1\n 2\n %s\n y\n 14\n" % (tar_file))
	os.close(write)
	try:
		p = subprocess.check_call(["./test"], stdin=read)
		return 0
	except:
		returncode = 1
return returncode

if __name__ == "__main__":
	main()

