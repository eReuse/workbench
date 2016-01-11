#!/usr/bin/env python
import time
import sys
# pip install tqdm
from tqdm import *

def sec(seconds):
    left = float(seconds) / 100

    for i in tqdm(range(100)):
        time.sleep(left)

def main(argv=None):
    seconds = sys.argv[1]
    left = float(seconds) / 100

    for i in tqdm(range(100)):
        time.sleep(left)

if __name__ == "__main__":

    sys.exit(main(sys.argv))
