#!/usr/bin/env python
import requests
import urllib2
import os
import sys

def get_lastreleases():
	try:
		r = requests.get('https://api.github.com/repos/eReuse/device-inventory/releases/latest')
	except Exception:
		sys.exit("Cannot connect.")
	return r.json()

def check_webstatus():
	try:
		r = requests.get('https://api.github.com/repos/eReuse/device-inventory/releases/latest')
	except Exception:
		sys.exit("Cannot connect.")

	if r.status_code == 200:
		return True
	else:
		return False

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
	
def check_space():
	if check_local_space() > check_iso_space():
		return True
	else:
		return False

def check_version():
	
	# ← Need to check if /var/lib/tftpboot/iso is empty or eReuse image does not exist
	
	files = os.listdir(os.path.join('/var/lib/tftpboot/iso'))
	for checking in files:
		local_version = checking.split('_')[1]
		number_local = local_version[1:-4].split('.')
		number_checks = output["tag_name"].split('.')
		i = 0
		for number in number_checks:
			if number > number_local[i]:
				return True
				break
			i = i + 1
	return False

def get_iso():
	url = output["assets"][0]["browser_download_url"]
		
	### DOWNLOAD ###
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
	
	# Move it
	origin = os.path.join('.', file_name)
	destination = os.path.join('/var/lib/tftpboot/iso', file_name)
	os.rename(origin_file, destination)
	print "Finished."

if __name__ == '__main__':
	
	output = get_lastreleases()
	
	if check_webstatus():
		if check_content_type("application/x-iso9660-image"):
			print "The content founded is a iso image"
			if check_version():
				print "Update %s is available" % (output["tag_name"])
				print "The new iso needs %sMB and you have %sMB available on your system." % (check_iso_space(),check_local_space())
				if check_space():
					print "You have space on your hard drive."
					get_iso()
				else:
					print "You have no space on your hard drive."
			else:
				print "No update available"
		else:
			print "The content founded is not a iso image"
	else:
		print "Unable to connect to GitHub."
