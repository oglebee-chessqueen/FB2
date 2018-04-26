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

	delay = 1 # Seconds to wait before moving on to next file
	tar_name = "tmp.tar.gz" # Tarball filename suffix
	program = "./test"		# Executable from test.c
	tar_cmd = "gzip" # Command used to tarball files
	tar_args = "-czf" # Arguments to use when tarballing
	img_file = 0					# Keep track if tar.gz read in is an image file or not. If so, will need to rename.

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
	i = 0

	#Keep running program unless something sets break condition
	while True:
		log(logfile, "\n")
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
		log(logfile, "Running Receiver for FIREBall image/housekeeping...")
		returncode = comm_command(program, tar_name)
		if returncode != 0:
			log(logfile, "Error executing command: %s --> Receiving --> %s" % (program, tar_name))
			continue		# Re-start recevier to try to get next file

		# Check that we now have a file called tmp.tar.gz before continuing:
		if tar_name in os.listdir(root+dir):
			filefound=True
		else:
			log(logfile, "Correct file not found - retry Receiver...")
			continue

		# If receiving worked, check the size of the new file
		size=os.path.getsize(tar_name)	/10.**6	# will be in bytes --> Mbytes
		if size < 5.0:			# File is less than 1 MBit; likely housekeeping and not image
			img_file = 0
			destPath = directories['hk']
			log(logfile, "File Size: %0.2f --> likely: Housekeeping.\n Sending to directory %s" % (size,destPath))
		elif size >= 5.0:
			img_file = 1
			destPath = directories['img']
			log(logfile, "File Size: %0.2f --> likely: Image.\n Sending to directory %s" % (size,destPath))
		else:
			log(logfile, "Something is wrong! Cannot read SIZE of TAR: Re-try receiving...")
			continue

		# Untar files and place in the correct directory, depending on if housekeeping or images
		returncode, filename = untar(tar_name, destPath)
		if returncode != 0:
			log(logfile,"De-compression of %s FAILED - likely corrupted file" % (tar_name))
			continue		# Re-start recevier to try to get next file
		else:
			log(logfile,"De-compression of %s PASSED to: %s" % (tar_name,destPath))

		# Check if img_file = 1;
		#      - if not: 1. Delete tmp.tar.gz
		#                   2. Restart to the top of the while loop because housekeeping
		#                       files are in the right spot.
		#			- if yes: 1. Open the fits file --> read header info for file name --> rename file to header.fits
		#                   2. Delete tmp.tar.gz
		#                   3. Restart to the top of the while loop because housekeeping
		#                       files are in the right spot.
		#

		if img_file == 0:
			# Delete tmp.tar.gzip
			log(logfile,"No image files: All housekeeping. Continue to Receiver for next file...")
			os.remove(tar_name)
			continue
		elif img_file ==1:
			# Open file opened by tar_name
			log(logfile,"Tar file containing FITS image removed. Continue to Receiver for next file...")
			#~ new_filename = read_fits(filename)
			#~ os.rename(os.path.join(directories["img"],filename),os.path.join(directories["img"],new_filename+".fits"))
			#~ log(logfile,"Image file renamed from: %s --> %s" % (os.path.join(directories["img"],filename),os.path.join(directories["img"],new_filename+".fits")) )
			os.remove(tar_name)
			continue






# Wrap print+file output together
def log(logfile, string):
	print(string)
	with open(logfile, 'a') as f:
		f.write(string + '\n')



def untar(file, destPath):
	if os.name == "posix":	# linux: untar using "tar -xzf file -C destPath"
		try:
			tar = tarfile.open(file, 'r:gz')
			files=tar.getnames()
			p=subprocess.call(["tar","-xzf",file,"-C",destPath])
			returncode = 0
		except:
			returncode = 1
			files = ""
	elif os.name == "nt": # windows: Untar using tarfile commands
		tar = tarfile.open(file, 'r:gz')
		files=tar.getnames()
		try:
			tar.extractall(path=destPath)
			tar.getnames()
			print tar
			returncode = 0
		except:
			returncode = 1
			files = ""
		tar.close()
	return returncode, files


# Method for running comm C-executable to transmit tar files to ground
def comm_command(program, tar_file):
	if os.name == "posix":		# linux: run ./test for transmission
		try:
			timeout = 3		# Set time for delay to check change in file size to exit receiver
			filename = tar_file
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
