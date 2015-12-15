#!/usr/bin/env python
import requests
import urllib2


import os
import sys
	
r = requests.get('https://api.github.com/repos/eReuse/DeviceInventory/releases/latest')

output = r.json()

content_type = output["assets"][0]["content_type"]
size = output["assets"][0]["size"]
url = output["assets"][0]["browser_download_url"]

if r.status_code != 200:
	print "Error to get the last release from GitHub."
	exit

# Space Left
st = os.statvfs('.')
space = st.f_bavail * st.f_frsize / 1024 / 1024
size = size / 1024 / 1024

print "The content founded is %s." % (content_type)
print "The new iso needs %s megabytes." % (size)
print "And you have %s megabytes left." % (space)

if size < space:
	print "Downloading iso image."
	
	# DOWNLOAD
	file_name = url.split('/')[-1]
	u = urllib2.urlopen(url)
	f = open(file_name, 'wb')
	meta = u.info()
	file_size = int(meta.getheaders("Content-Length")[0])
	print "Downloading: %s" % (file_name)

	file_size_dl = 0
	block_sz = 8192
	while True:
		buffer = u.read(block_sz)
		if not buffer:
			break

		file_size_dl += len(buffer)
		f.write(buffer)
		status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / file_size)
		status = status + chr(8)*(len(status)+1)
		print status,

	f.close()

