# MUST be run through virtualenv!:
#
# voldy:/home/fireball2/Communications/comsync-r15-port1/python_env/bin/python
#	(or in the folder: python_env/bin/python )
#
#
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
#
##
### MAJOR CHANGES:
##
#		- Files transmitted are no long compressed!
#		- Files need to be moved now through python os.Popen() command
#		- FITS files are now transmitted as TXT files --> change file extension
#

import os
import subprocess
import sys
import tarfile
import time
from datetime import datetime, timedelta
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

	# Initialize log file
	timeinit = datetime.now()
	logfile = "filetrack_rx_%02i%02i%02i_%02i%02i.log" % (
		timeinit.year % 100,
		timeinit.month,
		timeinit.day,
		timeinit.hour,
		timeinit.minute
	)

	# Hard-code one filename for Rx to write to every time
	filename = "rxdata.tar.gz"
	program = "./test"		# Executable from test.c
	filedir = "/home/fireball2/Communications/comsync-r15-port1/rxdata/"
	tardir = "/home/fireball2/Communications/comsync-r15-port1/rxtar/"
	num = 1
	delay = 5 # Seconds to wait before moving on to next file



	#Keep running program unless something sets break condition
	while True:
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

		# Receive tar file using data transfer C code
		try:
			# 1. Rx Purge
			# Try to purge RX after file transfer complete
			try:
				p = subprocess.Popen([program],
														 stdin=subprocess.PIPE,
														 stdout=subprocess.PIPE,
														 bufsize=1)
				pid = p.pid
				p.stdin.write("y\n y\n y\n 7\n")
				time.sleep(delay)		# Wait for purge to pass and not block up receiver?
				print "Rx purge complete"
				log(logfile,"Rx purge: SUCCESS")
			except:
				print "Rx purge didn't work?"
				log(logfile,"Rx purge: FAILED")

			# 2. Receive data
			timeout = 3		# Set time for delay to check change in file size to exit receiver
			log(logfile,"Running 1 Mbit transfer ...")
			print "Running 1 Mbit transfer..."
			# Tell ./test to receive a file
			p.stdin.write("12\n 4096\n 1\n 2\n %s\n" % (filename))
			# Use this to break from receiver (TRY)
			oldsize = 0
			while True:
				#print out
				time.sleep(timeout)
				size = os.path.getsize(filename)
				print size
				if size == 0:
					continue
				elif size == oldsize:
					print "file transfer complete"
					log(logfile,"file transfer complete: file size = %i bytes"%(size))
					os.kill(pid, 9)
					break
				oldsize = size
				returncode = 0

			# move tar file to tar directory
			try:
				newtar = "rxdata_%i.tar.gz"%(num)
				subprocess.call("cp "+filename+" "+tardir+newtar, shell=True)
				num += 1
				print "Moving tar to new directory SUCCESSFUL!"
				log(logfile,"Moving Rx tar to new directory: SUCCESSFUL!")
			except:
				print "Moving tar to new directory FAILED :("
				log(logfile,"Moving Rx tar to new directory: FAILED")
			# Untar file
			try:
				tar = tarfile.open(filename,'r:gz')
				tar.extractall(path=filedir)
				tar.close()
				print "Untarring Rx file SUCCESSFUL! Onto next file..."
				log(logfile,"Untarring Rx tar to new directory: SUCCESSFUL!")
			except:
				print "Untarring Rx FAILED :("
				log(logfile,"Untarring Rx tar to new directory: FAILED")

		except:
			print "Unable to open program."
			log(logfile,"UNABLE TO OPEN RX LINE!: ./test likely still open!!!!!")
			os.kill(pid, 9) # 9 or 15
			returncode = 1






# Wrap print+file output together
def log(logfile, string):
	print(string)
	with open(logfile, 'a') as f:
		f.write(string + '\n')









if __name__ == "__main__":
	main()
