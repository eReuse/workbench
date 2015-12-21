#!/usr/bin/env python
import subprocess
import os
import sys
try:
    import ConfigParser as configparser  # Python2
except ImportError:
    import configparser

def load_config():
    # https://docs.python.org/3.4/library/configparser.html
    path = os.path.dirname(__file__)
    config_file = os.path.join(path, 'config.ini')
    assert os.path.exists(config_file), config_file

    config = configparser.ConfigParser()
    config.read(config_file)  # donator.cfg merged here
    
    #print(config['DEFAULT']['DISC'])
    #print(config['DEFAULT'].getboolean('DISC'))
    #print(config['donator']['email'])
    
    # TODO set fallback values if config is empty
    # https://docs.python.org/3.4/library/configparser.html#fallback-values
    
    return config

def get_user_input(sdx_path):
    # XXX configurable user input fields
    config_erase = raw_input("Do you want to erase \"{0}\"? ".format(sdx_path))
    return config_erase

def do_erasure(device):
    return "Erasuring \"%s\"." % (device)

def main(argv=None):
    config = load_config()
    config_erase = config.get('DEFAULT', 'ERASE')
    dev = "/dev/"
    devs = os.listdir(dev)
    hdd = "sd"

    # Selecting only sd? "files"
    for file in devs:
        if file.startswith(hdd):
            if len(file) == 3:
                
                # Joining to path to start a erasure
                sdx_path = os.path.join("/dev/",file)
                print "Do a erasure on \"%s\"? %s" % (sdx_path,config_erase)
                if config_erase == "yes":
                    print do_erasure(sdx_path)
                elif config_erase == "ask":
                    erase = get_user_input(sdx_path)
                    if erase == "yes":
                        print do_erasure(sdx_path)

if __name__ == "__main__":
    sys.exit(main(sys.argv))
