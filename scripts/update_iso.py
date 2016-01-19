#!/usr/bin/env python
import requests
import urllib2
import time
import os
from os import listdir
from os.path import isfile, join

github = "https://api.github.com/repos/eReuse/device-inventory/releases/latest"
save_path = "/var/lib/tftpboot/iso/"


def check_local_space(save_path, r): #CHECK
    st = os.statvfs('.')
    return st.f_bavail * st.f_frsize / 1024 / 1024

def check_iso_space(save_path, r): #CHECK
    size = r.json()["assets"][0]["size"]
    return size / 1024 / 1024

def check_space(save_path, r): #CHECK
    print("{0}MB free space for {1}MB from iso.".format(check_local_space(save_path, r),check_iso_space(save_path, r)))
    if check_local_space(save_path, r) > check_iso_space(save_path, r):
        return True
    else:
        return False

def check_version(save_path, r):
    
    if len(os.listdir(save_path)) == 0:
        return True
    else:
        # Check number version to github
        number_checks = r.json()['tag_name'][1:].split('.')

        files = [f for f in listdir(save_path) if isfile(join(save_path, f))]
        for check in files:
            # Check if name eReuseOS_vXXX.iso exist.
            if '_v' in check:
                local_version = check.split('_')[1]
                number_local = local_version[1:-4].split('.')

                i = 0
                update = False
                
                for number in number_checks:
                    
                    # if is not on the number limit
                    if len(number_local) != i:
                        
                        #check if local version is minor number
                        if number_local[i] < number:
                            update = True
                            break
                            
                        # if local number is bigger, exit
                        elif number_local[i] > number:
                            exit("You have a niewer version")
                        
                    # if is equal but local number have more numbers than update version, exit
                    elif len(number_local) > len(number_checks):
                        exit("You have a niewer version")
                    
                    # if local number is equal but update version have more numbers available, then true
                    else:
                        if update == False and len(number_checks) > len(number_local):
                            update = True
                            break
                    
                    # Sum more nums to checks
                    i = i + 1
                
                # if local version have more number, then exit. NEED TO CHECK IT
                if update == False and len(number_checks) < len(number_local):
                    exit("You have a niewer version")

        return update

def download_iso(save_path, url):
    file_name = url.split('/')[-1]
    u = urllib2.urlopen(url)
    to_file = os.path.join(save_path, file_name)
    # +Add TRY if user cancel it, then remove the downloaded unfinished
    f = open(to_file, 'wb')
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
        speed = file_size 
        status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / file_size)
        status = status + chr(8)*(len(status)+1)
        print status,
        print buffer
    f.close()

def get_iso_asset(save_path, r):
    asset = 0
    detected = dict()
    detected["number"] = 0
    while True:
        try:
            log = detected[asset]
            if log["content_type"] == "application/x-iso9660-image" or log["content_type"] =="application/x-cd-image":
                detected["number"] = detected["number"] + 1
                number = detected["number"]
                detected[number] = asset
        except:
            asset = asset - 1
            break
        asset = asset + 1
    return detected

def ask_user(save_path, r):
    assets = r.json()["assets"] # Get Assets
    detected = get_iso_asset(save_path, r)
    print(detected)
    time.sleep(10)

    # IF more than 1 iso is detected or...
    valid = {"yes": True, "y": True, "ye": True,}
    time.sleep(10)
    if detected["number"] != 1:
        # MORE THAN 1, ASK WHAT WANT TO BE DOWNLOADED
        # +Add Need to give the option to choose what image to download
        i = 0
        while (i != detected["number"]):
            i = i +1
            print assets[detected[i]]["name"]
    else:
        # ONLY 1 ISO AVAILABLE
        size = assets[detected[1]]["size"]
        size_MB = size / 1024 / 1024
        choice = raw_input("Update to {0} (Size: {1}MB)? [y/N] ".format(assets[detected[1]]["name"],size_MB)).lower()
        if choice in valid:
            print assets[detected[1]]["browser_download_url"]
            download_iso(save_path, assets[detected[1]]["browser_download_url"])

def main(save_path, r):
    # Check free space
    if check_version(save_path, r) == True:
        print "Update available."
        if check_space(save_path, r) == True:
            # if space is true, ask to download
            ask_user(save_path, r)
        else:
            if len(os.listdir(save_path)) != 0:
                print("Some files found on `{0}`:".format(save_path))
                files = [f for f in listdir(save_path) if isfile(join(save_path, f))]
                print files
                deletion = raw_input("Do you want to delete them? ")
                valid = {"yes": True, "y": True, "ye": True,}
                if deletion in valid:
                    for rem in files:
                        delete = os.path.join(save_path,rem)
                        os.remove(delete)
                        print("deleted `{0}`.".format(delete))
                        # +add ummount
                    if check_space(save_path, r) == True:
                       ask_user(save_path, r)
    else:
        print "Already up-to-date."

if __name__ == "__main__":
    
    # Get latest releases
    r = requests.get(github)

    # Check if connection is ok
    if r.status_code != 200:
        print r.status_code
        exit("Cannot connect to server")

    # Start
    exit(main(save_path, r))
 
