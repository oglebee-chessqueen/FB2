# Define functions here!
#
#Method to wrap print+file output together
def log(string):
	print(string)
	logfile.write(string+'\n')

# Method for tar-ing image files:
def tar_image(file,compression):
	# Open image tarfile with tarfile
	returncode=0
	tar = tarfile.open(file+compression,'w:gz')
	try:
		tar.add(file)
		returncode=0
	except:
		log("tar.add() [FITS image] command failed")
		returncode=1
	tar.close()
	return returncode

# Method for tar-ing housekeeping
def tar_housekeeping(file,path,compression,files):
	tar = tarfile.open(file+compression,'w:gz')
	try:
		for name in files:
			tar.add(path+'\\'+name)
		returncode=0
	except:
		log("tar.add() [housekeeping] command failed")
		returncode=1
	tar.close()
	return returncode

# Method for running comm C-executable to transmit tar files to ground
def comm_command(program,tar_file):
	read, write = os.pipe()
	# IF Transmit:
	os.write(write, "y\n y\n y\n 11\n 128\n 10\n 2\n %s\n y\n 14\n" % (tar_file))
	os.close(write)
	# Run script
	p=subprocess.check_call(program,stdin=read)
	return p

#User-determined variables
directory = "C:\Users\User\Documents\FIREBall-2 python\\170831\\"   #"." #Directory to use

obc_directory = directory #""		# Directory on-board detector computer to look for new images + housekeeping files
gnd_directory = "C:\Users\User\Documents\FIREBall-2 python\170831_move_test\\"		# Directory to downlink compressed on-board files to and unzip
image_directory = "\\nuvutest\\"
filename_root = "image" #Substring to find in filenames
num0 = 000000 #File number you want to start on
# Housekeeping names not expected to change
housekeeping = ["alltemps.csv", "nuvupressure.csv", "power.csv", "pressure.csv", "dygraph-combined.js", "index-fireball.html"]
delay = 10 #Time to wait before moving on to next file
tarstring = ".tar.gz" #Suffic that identifies tarballs (e.g. '.gz', '.tar.gz' )
program = "./test"		# Executable from test.c					#"myprogram.sh"
tar_cmd = "gzip" #Command used to tarball files
tar_args = "-cvzf" #Arguments to use when tarballing

#Other variables
now = datetime.now()
dt = now-now		# Keep track of time from "now" to "current"
logpath = "filetrack_%02i%02i%02i_%02i%02i.log" % (now.year%100,now.month,now.day,now.hour,now.minute)
logfile = open(logpath,'w')
quit = False
i = 0
num = num0

#Modifications
directory = os.path.abspath(directory) #Make sure directory is absolute path
log("Checking directory: %s" % directory)


#Keep running program unless something sets break condition (quit=True)
while not(quit):
	# Log the start time
	current = datetime.now()
	dt = current - now
	print dt
	hk_filepath = obc_directory+"\\hk_%02i%02i%02i_%02i%02i%02i" % (current.year%100,current.month,current.day,current.hour,current.minute,current.second)
	logfile = open(logpath,'a')
	log(" ")
	log("Time: %02i%02i%02i_%02i:%02i:%02i" % (current.year%100,current.month,current.day,current.hour,current.minute,current.second))

	#Get filename for this image
	filename = "%s%06i.fits" % (filename_root,num)
	log("File: %s" % filename)
	logfile.close()

	#Create booleans to keep track of whether each file is found
	filefound = False
	tarballfound = False

	#Run through all files in directory and try to match names
	# THIS CHECK IS FOR IMAGES
	for f in os.listdir(obc_directory+image_directory):
		if filename in f and not tarstring in f: filefound=True
		elif filename in f and tarstring in f: tarballfound=True

	#If both file and tarball exist - just move on to next file
	if filefound and tarballfound:
		logfile = open(logpath,'a')
		log("Image, compressed image, and compressed housekeeping exist for %s -- Moving to next image." % filename)
		logfile.close()
		num+=1
		##dt = current - now

	#If file exists but no tarball, compress and call command
	elif filefound and not tarballfound:
		#Get absolute filepath
		#filepath = obc_directory + '/' + filename      # linux
		filepath = obc_directory+image_directory + filename       # windows (test)
		logfile = open(logpath,'a')
		#Execute tarball command
		returncode = tar_image(filepath,tarstring)
		log("Compressing to file: %s" % (filepath+tarstring))
		logfile.close()

		# Do IF dt = 0 or dt % 60 = 0 (every minute or so)
		#~ if (dt==0) or (dt.seconds%60==0):		# Idea was to not do this for every image, but maybe do anyway?
		# DO the same for housekeeping data
		hk_filepath=hk_filepath+"_%s%06i" % (filename_root,num)
		returncode = tar_housekeeping(hk_filepath,directory,tarstring,housekeeping)
		logfile = open(logpath,'a')
		#log("Return code = %i" % returncode)
		log("Compressing to file: %s" % (hk_filepath+tarstring))
		logfile.close()

		if returncode!=0:
			#Output error message
			logfile = open(logpath,'a')
			log("Error executing command: %s %s %s" % (tar_cmd,tar_args,filepath))
			logfile.close()
			#Set quit condition
			quit = True
			#Exit current loop
			break

		#Get filepath for new compressed file
		filepath += tarstring
		hk_filepath += tarstring
		logfile = open(logpath,'a')
		#Run program giving file path as argument
		# 1. Image tar
		log("--> Sending %s to comm board" % (filepath))
		###comm_command(program,filepath)

		#If program does not complete successfully
		if returncode!=0:
			log("Error executing command: %s %s" % (program,filepath))		#Output error message
			quit = True			#Set quit condition
			break					#Exit current loop

		elif returncode==0:
			log("%s successfully sent!" % (filepath))

		# 2. Housekeeping tar
		# Do IF dt = 0 or dt % 60 = 0 (every minute or so)
		#if (dt==0) or (dt.seconds%60==0):
		log("--> Sending %s to comm board" % (hk_filepath))
		###comm_command(program,hk_filepath)
		#If program does not complete successfully
		if returncode!=0:
			log("Error executing command: %s %s" % (program,hk_filepath))		#Output error message
			quit = True			#Set quit condition
			break					#Exit current loop
		elif returncode==0:
			log("%s successfully sent!" % (hk_filepath))

		logfile.close()
		#Increment image number
		num+=1
		logfile = open(logpath,'a')
		log("Next image number looking for: %06i" % (num))
		#~ #Wait the given amount of time before moving on
		#~ # Actually, don't wait --> continue to next, if available
		logfile.close()
		#~ time.sleep(delay)
		##dt = current - now

	#If no file or tarball exist, probably just not created yet. Just wait.
	elif not filefound and not tarballfound:
		logfile = open(logpath,'a')
		#Wait the given amount of time before moving on
		log("FITS file not created/found yet.")
		log("Sleeping... %2i seconds" % (delay))
		logfile.close()

		# Still send back housekeeping data:
		if (dt==0) or (dt.seconds%60<delay):
			returncode = tar_housekeeping(hk_filepath,directory,tarstring,housekeeping)
			logfile = open(logpath,'a')
			#log("Return code = %i" % returncode)
			log("Compressing to file: %s" % (hk_filepath+tarstring))
			hk_filepath += tarstring
			log("--> Sending %s to comm board" % (hk_filepath))
			###comm_command(program,hk_filepath)

			#If program does not complete successfully
			if returncode!=0:
				log("Error executing command: %s %s" % (program,hk_filepath))		#Output error message
				quit = True			#Set quit condition
				break					#Exit current loop

			elif returncode==0:
				log("%s successfully sent!" % (hk_filepath))

			logfile.close()
		# Still send down
		time.sleep(delay)
		##dt = current - now

	#Only remaining condition is if tarball exists but no file, which would be an error.
	else:
		#Output error message
		logfile = open(logpath,'a')
		log("WARNING: Tarball found for %s but no raw image." % filepath)
		logfile.close()
		#Set quit condition
		quit = True
		#Exit loop
		break

	#log("End time: %02i%02i%02i_%02i:%02i:%02i" % (now.year%100,now.month,now.day,now.hour,now.minute,now.second))
	logfile.close()
