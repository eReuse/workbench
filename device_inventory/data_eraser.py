#!/usr/bin/env python
import subprocess
import os
import sys
try:
    import ConfigParser as configparser  # Python2
except ImportError:
    import configparser

    import device_inventory

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

def get_hdinfo(path,value):
    return subprocess.Popen(["lsblk",path,"--nodeps","-no",value], stdout=subprocess.PIPE)

def get_user_input(sdx_path):
    size = get_hdinfo(sdx_path,"size").stdout.read()
    model = get_hdinfo(sdx_path,"model").stdout.read()
    disk = get_hdinfo(sdx_path,"tran").stdout.read()
    print "Selected %s (Model: %s) (Size:%s) (Type: %s)." % (sdx_path,model.rstrip(" \n"),size.rstrip(" \n"),disk.rstrip(" \n"))
    config_erase = raw_input("Do you want to erase \"{0}\"? [y/N] ".format(sdx_path))
    return config_erase

def erasetor(dev, steps="0"):
     try:
         subprocess.call(["shred","-zvn",steps,dev])
     except ValueError:
         print "ERROR:root:Cannot erase the hard drive {0}".format(dev)
        

def do_erasure(sdx):
    config = load_config()
    erase = config.get('DEFAULT', 'ERASE')

    if erase == "yes":
        print erasetor(sdx)
    elif erase == "ask":
        erase = get_user_input(sdx)
        if erase.lower().strip() == "y" or erase.lower().strip() == "yes":
            print erasetor(sdx)

def main(argv=None):
    device = sys.argv[1]
    do_erasure(device)

if __name__ == "__main__":
# checking priveleges
    if os.geteuid() !=  0:
        sys.exit("Must be root to erase data.")

    try:
        arg_var = sys.argv[1]
    except IndexError:
        exit("No devices selected.")

    if len(arg_var) < 7:
        exit("Device not valid.")
        
    # Start
    if os.path.exists(arg_var):
        sys.exit(main(sys.argv))
    else:
        exit("Device does not exit.")
