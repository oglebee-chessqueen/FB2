#~ nm = "im00.tar.gz"
#~ nm = "im4096_3.tar.gz"
#~ nm = "image_000000.fits"		# 22: 0
#~ nm = "image000000.fits" 	# 0x16+0xff: 21521; 22: 8823
#~ nm = "image000019.fits"  # 0x16+0xff: 36924; 22: 14601
#~ nm = "im0.fits"
#~ nm = "tmp2test00.fits"
#~ nm = "test.fits"
#~ nm = "image000022.fits"  # 0x16+0xff: 133; 22: 133
#~ nm = "image000055.fits"  # 0x16+0xff: 5399; 22: 5399
#~ nm = "hk.tar.gz"
#~ nm = "pressure.csv"
import os

#~ f = open("img04096.tar.gz", "rb")
#~ size = os.path.getsize(nm) / 10.**6		# Prints total file size, in bytes --> Mbytes
#~ print size

#~ try:
	#~ with open(nm, "rb") as f:
		#~ count = 0
		#~ byte = f.read(1)
		#~ while byte != "":
			#~ byte = ord(byte)
			#~ if byte == 0xFF or byte == 0x16:
				#~ count += 1
			#~ byte = f.read(1)
#~ except:
	#~ pass

#~ print nm, count


def count_bytes(filename):
	counts = [0] * 256
	try:
		with open(filename, "rb") as f:
			byte = f.read(1)
			while byte != "":
				counts[ord(byte)] += 1
				byte = f.read(1)

		return counts
	except:
		pass

filenames = [ # Comment all but the two files to be tested
	#~ "tmp2test00.fits",
	"test.txt.working",
	"test.txt",
]
print "%sB %s" % (os.path.getsize(filenames[0]), filenames[0])
print "%sB %s" % (os.path.getsize(filenames[1]), filenames[1])
counts_a = count_bytes(filenames[0])
counts_b = count_bytes(filenames[1])
for i in range(256):
	if counts_a[i] != counts_b[i]:
		print "0x%02X %7s %7s %2d" % (i, counts_a[i], counts_b[i], counts_a[i] - counts_b[i])
		#~ print "{:08b} {:>7} {:>7}".format(i, counts_a[i], counts_b[i])
