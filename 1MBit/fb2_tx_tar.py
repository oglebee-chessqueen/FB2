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
#			- Compress new image file and existing housekeeping files (together)
#			- Send each compressed file through the 1 MBit transmitter/receiver c-code
#			- increment +1 to image file count.
#
##
### MAJOR CHANGES:
##
#		- Files no longer compressed - send down as-is
#		- FITS files --> Converted to TXT files (including header info)
#
#
# 	30 May 2018 - K. Hoadley

import os
import subprocess
import sys
import tarfile
import time
from datetime import datetime, timedelta
#from astropy.io import fits
#import numpy
#~ import shutil


def main():
	if os.name == "posix":
		root = "/home/fireball2"
		dir = '/'
	elif os.name == "nt": # windows
		root = "C:\\Users\\Keri Hoadley\\Documents\\FIREBall-2\\python"
		dir = '\\'
	else:
		print "Unrecognized platform, exiting."
		exit(1)

	directories = {
		"hk": "data/",
		"img": "data/",
		#~ "img": ""
	}

	for key, value in directories.iteritems():
		directories[key] = os.path.normpath(os.path.join(root, value))+dir

	filename_root = "image" # Substring to find in filenames
	#### INCORPORATES OPTIONAL ARG at end of file call: python fb2_tx.py [number]
	#### If number is called, will start from there
	#### In no number called, will start at 0
	if len(sys.argv) == 2:
		print "Arguments called: ", sys.argv[1]
		filenum0 = int(sys.argv[1])
	else:
		filenum0 = 0			# IMAGE File number you want to start on
	print "Initial starting number: ", filenum0
	#~ filenum0 = 0 # File number you want to start on

	# Housekeeping names not expected to change
	housekeeping = [
		"alltemps.csv",
		"power.csv",
		"discretecom.csv",
		"waterpress.csv",
	]
	delay = 20 # Seconds to wait before moving on to next file
	program = "./test"		# Executable from test.c
	outfile = "txdata.tar.gz"
	num = 0
	tardir = '/home/fireball2/Documents/Communications/comsync-r15/txtar/'
	packet = 512		# packet size to use, up to 4096


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
		#~ for key, value in directories.iteritems():
			#~ directories[key] = os.path.join(value, datetime.now().strftime("%y%m%d"))
			#~ print directories[key]
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
		##### CHANGE IMAGE DIRECTORY HERE #####
		filepath = os.path.join(directories["img"]+'180526', filename)#datetime.now().strftime("%y%m%d"), filename)
		#print filepath

		log(logfile, "Next Image File: %s" % filename)

		# Keep track of whether each file is found
		filefound = os.path.isfile(filepath)

		# If file exists:
		if filefound:
			# 1. Create a copy of image.fits in backup drives
			returncode = backup_fits(filepath, filename)
			if returncode != 0:
				log(logfile,"Copy of %s FAILED --> continuing..." % (filename))
			else:
				log(logfile,"%s Copied to USB Drives!" % (filename))

			######## Don't do this to send down fits file ########
			# 2. Tar image + housekeeping files together to one file
			# Expand housekeeping to full directory location
			housefiles = []
			for hk in housekeeping:
				housefiles.append(os.path.join(directories["hk"]+datetime.now().strftime("%y%m%d"),hk))
			returncode = tar_files(filepath, housefiles, outfile, logfile)	# All files in this compression file!!
			#time.sleep(20)
			# move tar file to tar directory
			try:
				newtar = "txdata_%i.tar.gz"%(num)
				subprocess.call("cp "+outfile+" "+tardir+newtar, shell=True)
				num += 1
				print "Moving tar to new directory SUCCESSFUL!"
				log(logfile,"Moving Tx tar to new directory: SUCCESSFUL!")
			except:
				print "Moving tar to new directory FAILED :("
				log(logfile,"Moving Tx tar to new directory: FAILED")
			# Add delay based on file size
			filesize = os.path.getsize(outfile)
			size_delay = (filesize*8/1e6)+((filesize/packet)*0.001)
			time.sleep(5)

			# 2. Send TAR file (outfile) through transmitter
			returncode = comm_command(program, outfile, packet)
			if returncode != 0:
				log(logfile, "Error executing command: %s %s" % (program, outfile))
				break
			else:
				log(logfile, "%s successfully sent!" % (outfile))		#new_filepath)

			# Now, delay a short time to make sure receiver is cleared
			filenum += 1
			log(logfile, "Next image number looking for: %06i" % (filenum))
			log(logfile, "Waiting %d for checking next file..." % (size_delay))
			#time.sleep(delay)		# Add delay to allow for Rx PURGE time
			time.sleep(size_delay)

		#If no file or tarball exist, probably just not created yet. Just wait.
		elif not filefound:
			# Wait the given amount of time before moving on
			log(logfile, "FITS file not created/found yet.")
			log(logfile, "Sleeping... %2i seconds" % (delay))

			# Still send down
			time.sleep(delay)

		# If tarball exists but no file. This is always an error.
		else:
			log(logfile, "SOMETHING IS WRONG -- BREAKING.")
			break





# Wrap print+file output together
def log(logfile, string):
	print(string)
	with open(logfile, 'a') as f:
		f.write(string + '\n')




def tar_files(img, hk, compression, logfile):
	'''
	img and hk files already have directories attached to them
	'''
	files = [img]
	for i in hk:
		files.append(i)
		print files
	if os.name == "posix":		# linux: use Popen for command line tarball
		tar = compression
		try:
			p=subprocess.call(["tar","-czf",tar,files[0],files[1],files[2],files[3],files[4]])
			log(logfile,"File compression: SUCCESS - img file: %s" % (img))
			returncode = 0
		except:
			print "subprocess.call() did not work for %s tar" % (tar)
			log(logfile,"File compression: FAILED - img file: %s" % (img))
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
def comm_command(program, tar_file, packet):
	if os.name == "posix":		# linux: run ./test for transmission
		read, write = os.pipe()
		# IF Transmit:
		os.write(write, "y\n y\n y\n 11\n %i\n 1\n 2\n %s\n y\n 14\n" % (packet,tar_file))
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




def backup_fits(filename,img):
	'''
	Use to back up image fits files to USB drives in:
	/home/fireball2/databackup0
	/home/fireball2/databackup1
	filename = file name of image + its path
	img = image name only (no path)
	'''
	destPath1 = "/home/fireball2/databackup0"
	destPath2 = "/home/fireball2/databackup1"
	origFile = filename
	if os.name == "posix":		# linux: run ./test for transmission
		try:		# Move to USB 1, then 2
			newfile1 = os.path.join(destPath1, img)
			subprocess.Popen(["cp", "-v", origFile, newfile1])
			newfile2 = os.path.join(destPath2, img)
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
