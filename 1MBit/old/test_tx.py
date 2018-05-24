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


	#Other variables
	timeinit = datetime.now()
	delay = 15
	program = "./test"		# Executable from test.c
	logfile = "filetrack_txTEST_%02i%02i%02i_%02i%02i.log" % (
		timeinit.year % 100,
		timeinit.month,
		timeinit.day,
		timeinit.hour,
		timeinit.minute
	)
	i = 0


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
		filename = "test.fits"

		log(logfile, "--> Sending %s to comm board" % (filename))
		returncode = comm_command(program, filename)
		if returncode != 0:
			log(logfile, "Error executing command: %s %s" % (program, filename))
			break
		else:
			log(logfile, "%s successfully sent!" % (filename))

		# Now, delay a short time to make sure receiver is cleared
		# and re-started
		time.sleep(delay)






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

	return returncode




if __name__ == "__main__":
	main()
