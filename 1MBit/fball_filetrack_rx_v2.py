#!/usr/bin/env python2

#
# Handles recieving a new compressed file with either the new image or houskeeping files
# on the GSE during flight and de-compresses them, remains them, and puts them in appropriate
# directories:
#			- Turn receiver on to receive new file: tmp.tar.gz
#			- Close the receiver
#			- De-compress the tar file
#      - IF DE-COMPRESSION FAILS:
#						- Make note in logfile of the time or receiving file and continue
#			- IF DE-COMPRESSION PASSES:
#						- Use size of tar to determine where the files need to go (if < 1 MB, houekeeping file likely)
#						- Place file in correct destination path
#						- IF FILE IS IMAGE: Open image, pull filename from header, and rename file to header.fits
#      - Turn receiver on, wait for next file
#

import os
import subprocess
import sys
import tarfile
import time
from datetime import datetime
#~ from astropy.io import fits


def main():
	if os.name == "posix":
		root = "/home/fireball2/Communications/comsync-r15-port1"
		dir = '/'
	elif os.name == "nt": # windows
		root = "C:\\Users\\User\\Documents\\FIREBall-2 python\\"
		dir = '\\'
	else:
		print "Unrecognized platform, exiting."
		exit(1)

	directories = {
		"hk": "test_python_receiver",
		"img": "test_python_receiver/images"
	}

	for key, value in directories.iteritems():
		directories[key] = os.path.normpath(os.path.join(root, value))+dir

	filename_root = "image_170923_"
	housekeeping = [
		"alltemps_170923.csv",
		"nuvupressure_170923.csv",
		"power_170923.csv",
		"pressure_170923.csv",
		#~ "dygraph-combined.js",
		#~ "index-fireball.html"
	]

	delay = 1 # Seconds to wait before moving on to next file
	num0 = 0
	program = "./test"		# Executable from test.c

	#Other variables
	timeinit = datetime.now()
	dt = 0		# Delta time from "now" to "current"
	logfile = "filetrack_rx_%02i%02i%02i_%02i%02i.log" % (
		timeinit.year % 100,
		timeinit.month,
		timeinit.day,
		timeinit.hour,
		timeinit.minute
	)

	filenum = num0


	#Keep running program unless something sets break condition
	while True:
		#~ log(logfile, "\n")
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

		# Receive file using data transfer C code
		# Start a counter: We will be transmitting down 5 files in a row:
		# 1. - Image (.fits)
		# 2.--5. - Housekeeping (.csv)
		for i in range(0,len(housekeeping)+1):
			if i == 0:		#Transmitting down fits
				# Define filename
				filename = "%s%06i.fits" % (filename_root, filenum)
				#~ filepath = os.path.join(directories["img"], filename)
				log(logfile, "Running Receiver for FIREBall image...")
				returncode = comm_command(program, filename)

				if returncode != 0:
					log(logfile, "Error executing command: %s --> Receiving --> %s" % (program, filename))
					break	# Re-start recevier to try to get next file
				filenum += 1

			else:		# Housekeeping files
				# Define filename
				filename = housekeeping[i-1]
				#~ filepath = os.path.join(directories["hk"], filename)
				log(logfile, "Running Receiver for FIREBall housekeeping %s..." % (filename))
				returncode = comm_command(program, filename)
				if returncode != 0:
					log(logfile, "Error executing command: %s --> Receiving --> %s" % (program, filename))
					continue		# Re-start recevier to try to get next file










# Wrap print+file output together
def log(logfile, string):
	print(string)
	with open(logfile, 'a') as f:
		f.write(string + '\n')





# Method for running comm C-executable to transmit tar files to ground
def comm_command(program, filename):
	if os.name == "posix":		# linux: run ./test for transmission
		try:
			timeout = 1		# Set time for delay to check change in file size to exit receiver
			#~ filename = tar_file
			print "Running program..."
			p = subprocess.Popen(
				[program],
				stdin=subprocess.PIPE,
				stdout=subprocess.PIPE,
				bufsize=1)
			pid = p.pid
			###p.stdin.write('w\n')
			p.stdin.write("y\n y\n y\n 12\n 256\n 1\n 2\n %s\n" % (filename))
			# Use this to break from receiver (TRY)
			oldsize = 0
			while True:
				time.sleep(timeout)
				size = os.path.getsize(filename)
				print size
				if size == 0:
					continue
				elif size == oldsize:
					print "file transfer complete"
					os.kill(pid, 9) # 9 or 15
					break
				oldsize = size
				returncode = 0
		except:
			print "Unable to open program."
			returncode = 1
	elif os.name == "nt": # windows: ./test won't run, so just skip
		print "Running receiver code (Win: simulated): %s" % (tar_file)
		time.sleep(10)
		returncode = 0
	return returncode




def read_fits(filename):
	# Open fits with astropy
	hdulist = fits.open(filename)
	# CHANGE TO CORRECT CALLABLE ONCE KNOWN
	hrd = hdulist[0].header		# Can do hdr.comments[' '] to check header comments
	hdulist.close()
	return hdr



if __name__ == "__main__":
	main()
