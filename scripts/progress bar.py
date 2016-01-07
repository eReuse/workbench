import time
import sys

def main(argv=None):
    seconds = sys.argv[1]

    toolbar_width = 50
    left = float(seconds) / toolbar_width

    # setup toolbar
    sys.stdout.write("[%s]" % (" " * toolbar_width))
    sys.stdout.flush()
    sys.stdout.write("\b" * (toolbar_width+1)) # return to start of line, after '['

    for i in xrange(toolbar_width):
        time.sleep(left) # do real work here
        # update the bar
        sys.stdout.write("-")
        sys.stdout.flush()

    sys.stdout.write("\n")

if __name__ == "__main__":

    sys.exit(main(sys.argv))
