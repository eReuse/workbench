eReuse.org Workbench
####################

.. code-block::

    Usage: erwb [OPTIONS]

    Create a hardware report of your computer with components, serial numbers,
    testing, benchmarking, erasing, and installing an OS.

    By default Workbench only generates a report of the hardware
    characteristics of the computer, so it is safe to use. Parametrize it to
    make workbench perform tests, benchmarks... generating a bigger report
    including the results of those actions.

    You must run this software as root / sudo.

    Options:
      -b, --benchmark / --no-benchmark
                                      Benchmark the components using sysbench and
                                      other tools.
      -st, --smart [Short|Extended]   Perform a SMART test to all the data storage
                                      units.
      -e, --erase [EraseBasic|EraseSectors]
                                      Erase all data storage units.
      -es, --erase-steps INTEGER RANGE
                                      Number of erasure STEPS.
      --erase-leading-zeros / --no-erase-leading-zeros
                                      Shall we perform an extra erasure step
                                      writing zeros?
      -ss, --stress INTEGER RANGE     Run stress test for the given MINUTES (0 to
                                      disable)
      -i, --install TEXT              The name of the FSA OS to install, without
                                      the ".fsa" extension. The file has to be in
                                      /media/workbench-images
      -sr, --server URL               Connect to a WorkbenchServer at the
                                      specified URI. This will activate USBSneaky
                                      module, load the settings from the server,
                                      and keep indefinitely waiting for an USB
                                      tobe plugged-in.
      --sync-time / --no-sync-time    Sync the time with the Internet before
                                      executing the Workbench. Print a warning if
                                      it cannot sync (ex. no Internet).
      -j, --json FILE                 Write the resulting report to a JSON file.
      --submit URL                    If set, submits the resulting Snapshot to a
                                      passed-in Devicehub.Provide a valid URL with
                                      scheme, username, password and host.
      --debug / --no-debug            Add extra debug information to the resulting
                                      snapshot?
      -h, --help                      Show this message and exit.

      Ex. sudo erwb --benchmark --smart Short --erase EraseSectors --json out.json

      will generate a hardware report plus benchmarks, a short SMART test of all
      data storage units, and a certified erasure of all data storage units,
      saving the resulting report as 'out.json'.

`See an example JSON report <https://github.com/eReuse/devicehub-teal/blob/master/ereuse_devicehub/dummy/files/asus-eee-1000h.snapshot.11.yaml>`_.

Workbench can be used in an `USB or CD <https://github.com/ereuse/workbench-live>`_,
or even `over the network through PXE <https://github.com/ereuse/workbench-server>`_,
specially useful when erasing and installing OSes or working
with many computers.

Workbench uses several well-known Linux packages to perform each
action, avoiding re-inventing the wheel. It is used
professionally by refurbishers and regular companies to register,
prepare, and track their devices, and has great emphasis in data
correctness. Workbench is free software from `eReuse.org <https://ereuse.org>`_.

Download
********
You can `get Workbench directly in an ISO ready to use <https://nextcloud.pangea.org/index.php/s/ereuse>`_
(go to `workbench-live` folder) or install it as a python package (see next section).

Installation
************
Workbench should work in any Linux as long as it has the packages below.
It is guaranteed to work in Debian 9.

1. Install the `debian packages <requirements.debian.txt>`_, like
   the following way ``cat requirements.debian.txt | sudo xargs apt install -y``.
2. ``sudo pip3 install ereuse-workbench --pre -U``

Note that you need to install this as sudo, as the software can only
be run with root due to the tools it uses.

Usage
*****
Execute Workbench through the CLI or directly in Python.

From a python file you can:

.. code-block:: python

    from ereuse_workbench.workbench import Workbench
    erwb = Workbench() # Check the docs of this class for more info
    erwb.run()

Testing
*******
1. Clone this repository and go to the repository main folder.
2. Install Workbench as `pip3 install -e .[test] -r requirements.txt`.
3. Run the tests with `python3 setup.py test`.

Note that you do not need to be root to execute tests, and that
they can be executed in Mac and Windows, as they do not use any
of the system tools, but stubs.

Known limitations
*****************

- Unsupported USB network adaptors.
- It cannot not install Windows OS.
