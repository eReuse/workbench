#!/usr/bin/env python
import requests
import urllib2
import os

def get_lastreleases():
	r = requests.get('https://api.github.com/repos/eReuse/DeviceInventory/releases/latest')
	return r.json()

def check_webstatus():
	if r.status_code != 200:
		print "Error to get the last release from GitHub."
		exit
	return r.status_code

def check_content_type(content):
	if output["assets"][0]["content_type"] == content:
		return True
	else:
		return False

def check_local_space():
	st = os.statvfs('.')
	return st.f_bavail * st.f_frsize / 1024 / 1024

def check_iso_space():
	size = output["assets"][0]["size"]
	return size / 1024 / 1024

def check_version():
	files = os.listdir(os.path.join('/var/lib/tftpboot/iso',))
	for checking in files:
		if file == "eReuseOS_v7.0.iso":
			print "true"


def get_iso():
	url = output["assets"][0]["browser_download_url"]
	if size < space:
		print "Downloading iso image."
		
		''' DOWNLOAD '''
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

if __name__ == '__main__':
	
	output = get_lastreleases()

	if check_content_type("application/x-cd-image"):
		print "The content founded is a iso image"
		print "The new iso needs %sMB and you have %sMB available on your system." % (check_iso_space(),check_local_space())
	else:
		print "The content founded is not a iso image"	
		
	files = os.listdir(os.path.join('/var/lib/tftpboot/iso',))
	for checking in files:
		local_version = checking.split('_')[1]
		print checking
		print local_version[1:-4]
		if local_version[1:-4] == output["tag_name"]:
			print "true"
		else:
			print "false"

