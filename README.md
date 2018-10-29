# eReuse.org Workbench
Create a hardware report (JSON) of your computer including components,
serial numbers, testing (SMART and stress test), benchmarking (sysbench),
erasing (using certified tools and well-known standards),
and installing an OS.

You parametrize Workbench to execute the actions you want and then
runs without user interaction, generating a human and machine 
friendly report in JSON. This report can be uploaded to the IT Asset
Management System [Devicehub](https://github.com/ereuse/devicehub-teal).
Check example reports [here](https://github.com/eReuse/devicehub-teal/blob/master/ereuse_devicehub/dummy/files/asus-eee-1000h.snapshot.11.yaml),
[here](https://github.com/eReuse/devicehub-teal/blob/master/ereuse_devicehub/dummy/files/dell-optiplexgx520.snapshot.11.yaml),
and [here](https://github.com/eReuse/devicehub-teal/blob/master/ereuse_devicehub/dummy/files/lenovo-3493BAG.snapshot.11.yaml).

Workbench can be used in an [USB or CD](https://github.com/ereuse/workbench-live),
or even [over the network through PXE](https://github.com/ereuse/workbench-server),
specially useful when erasing and installing OSes or working
with many computers.

This repository is the stand-alone core version of Workbench.

Workbench uses several well-known Linux packages to perform each
action, avoiding re-inventing the wheel. It is used
professionally by refurbishers and regular companies to register,
prepare, and track their devices, and has great emphasis in data
correctness. Workbench is free software from [eReuse.org](https://ereuse.org).

## Installation
Workbench is developed and tested in Debian 9, and it should
work in any Debian based OS, even in any Linux as long as the OS
has the debian packages listed below.

1. Install the [debian packages](debian-requirements.txt), like
   the following way `cat debian-requirements.txt | xargs apt install -y`.
2. `pip3 install ereuse-workbench --pre -U`

## Usage
Execute Workbench through the CLI or directly in Python.

To use the CLI check the help for more info: `$ erwb --help`

From a python file you can:
```python
    from ereuse_workbench.workbench import Workbench
    erwb = Workbench() # Check the docs of this class for more info
    erwb.run()
```

## Testing
1. Clone this repository and go to the repository main folder.
2. Install Workbench as `pip3 install -e .[test] -r requirements.txt`.
3. Run the tests with `python3 setup.py test`

Tests can be run in Windows an Mac machines too, as they use
stubs instead of accessing the OS packages.

## Known limitations
We want to overcome them in the future :-)

- Unsupported USB network adaptors.
- It cannot not install Windows OS.
