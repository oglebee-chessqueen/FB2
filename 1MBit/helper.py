#!/usr/bin/env python2
import os
import subprocess
import time

def main():
	timeout = 3
	filename = "./test.dat"

	p = subprocess.Popen(
		["./fakeRX", "30000000"],
		stdin=subprocess.PIPE,
		stdout=subprocess.PIPE,
		bufsize=1
	)
	pid = p.pid
	p.stdin.write('w\n')

	oldsize = os.path.getsize(filename)
	while True:
		time.sleep(timeout)
		size = os.path.getsize(filename)
		print size
		if size == oldsize:
			print "file transfer complete"
			os.kill(pid, 15) # or 9
			break


if __name__ == "__main__":
	main()
