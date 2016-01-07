import time
import sys
from tqdm import *

def main(argv=None):

    seconds = sys.argv[1]

    toolbar_width = 50
    left = float(seconds) / 100

    for i in tqdm(range(100)):
        time.sleep(left)

if __name__ == "__main__":

    sys.exit(main(sys.argv))
