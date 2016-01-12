#!/usr/bin/env python
import requests
import urllib2

def download_iso(url):
    file_name = url.split('/')[-1]
    u = urllib2.urlopen(url)
    f = open(file_name, 'wb')
    meta = u.info()
    file_size = int(meta.getheaders("Content-Length")[0])
    print "Downloading: {0} {1}MB".format(file_name, file_size)

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

def main(r):
    assets = r.json()["assets"] # Get Assets

    asset = 0
    detected = dict()
    detected["number"] = 0
    while True:
        try:
            log = assets[asset]
            if log["content_type"] == "application/x-iso9660-image" or log["content_type"] =="application/x-cd-image":
                detected["number"] = detected["number"] + 1
                number = detected["number"]
                detected[number] = asset
        except:
            asset = asset - 1
            break
        asset = asset + 1

    # IF more than 1 iso is detected or...
    valid = {"yes": True, "y": True, "ye": True,}

    if detected["number"] != 1:
        # MORE THAN 1, ASK WHAT WANT TO BE DOWNLOADED
        i = 0
        while (i != detected["number"]):
            i = i +1
            print assets[detected[i]]["name"]
    else:
        # ONLY 1 ISO AVAILABLE
        size = assets[detected[1]]["size"]
        size_MB = size / 1024 / 1024
        choice = raw_input("New update is available. \nUpdate to {0} (Size: {1}MB)? [y/N] ".format(assets[detected[1]]["name"],size_MB)).lower()
        print choice
        if choice in valid:
            print assets[detected[1]]["browser_download_url"]
            download_iso(assets[detected[1]]["browser_download_url"])


if __name__ == "__main__":
    
    # Get latest releases
    r = requests.get("https://api.github.com/repos/eReuse/device-inventory/releases/latest")

    # Check if connection is ok
    if r.status_code != 200:
        print r.status_code
        exit("Cannot connect to server")

    # Start
    exit(main(r))
 
