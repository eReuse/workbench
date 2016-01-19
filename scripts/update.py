#!/usr/bin/env python
import requests
import urllib2
import time
import os
from os import listdir
from os.path import isfile, join

github = "https://api.github.com/repos/eReuse/device-inventory/releases/latest"
path = "/var/lib/tftpboot/iso/"

def get(url):
    return requests.get(url)

def status(url):
    if url.status_code != 200:
        exit("ERROR: Cannot connect to GitHub.")
    elif url.status_code == 200:
        print("OK: Connected to GitHub.")

def get_latest(url):
    asset = 0
    latests = dict()
    latests["number"] = 0
    while True:
        try:
            log = assets[asset]
            if log["content_type"] == "application/x-iso9660-image" or log["content_type"] =="application/x-cd-image":
                latests["number"] = latests["number"] + 1
                number = latests["number"]
                latests[number] = asset
        except:
            asset = asset - 1
            break
        asset = asset + 1
    print latests
    return latests

def check_updates(path, url):
    get_latest(url)

def main(path, github):
    # Contact to GitHub API
    received = get(github)
    
    # Check if request has succeed
    status(received)
    
    # Convert the info from api to a json
    latest = received.json()

    # Check if update is available
    check_updates(path, latest)



if __name__ == "__main__":
    exit(main(path, github))
