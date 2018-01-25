# eReuse.org Workbench
The eReuse.org Workbench is a set of tools and services to assist the preparation for reuse and
traceability of digital devices (capture of hardware characteristics, hardware rating and testing,
secure deletion of data and install Linux OS).

## Features
- Run in an unattended way without the need for additional steps rather than powering up the
  computer.
- Provides documents for deletion of data, tests of operation, hardware information and serial
  numbers for traceability.
- Install Linux OS in record-time.
- Mass process network-connected computers with
  [Workbench Server](https://github.com/ereuse/workbench-server).

## Requirements
* Debian based Linux. Tested with Debian 9. 

Our installation script automatically installs [debian packages](debian-requirements.txt) and 
[python libraries](requirements.txt).

If you want to erase the hard-drive of a computer you will need to execute Workbench in a live cd.
We offer a live-cd with a pre-configured Workbench that connects to Workbench Server in
[Workbench Live](https://github.com/ereuse/workbench-live). You can use this project to customize
a workbench live that suits your needs.

## Installation
Download this project (clone it or with a zip) and then execute with root (as it will install as a
command-line too) `{project-folder}/scrpits/install.sh {project-folder}`, where `{project-folder}`
is the path where your project is. So, for example, if the path of your project is
`~/Documents/workbench`, then execute `~/Documents/workbench/scripts/install.sh
~/Documents/workbench`.

## Usage
Execute `erwb` as root, like `sudo erwb`. 

The process will generate a JSON file with the hardware description in it, for example:
```json
{
    "@type": "Snapshot",
    "_uuid": "c58060c1-72e9-4638-893b-a928e9fb9c9c",
    "comment": "A description of this PC.",
    "components": [
        {
            "@type": "GraphicCard",
            "manufacturer": "Acme Corporation",
            "memory": 256.0,
            "model": "82945G/GZ Integrated Graphics Controller"
        },
        {
            "@type": "HardDrive",
            "benchmark": {
                "@type": "BenchmarkHardDrive",
                "readingSpeed": 44.7,
                "writingSpeed": 24.8
            },
            "interface": "ata",
            "manufacturer": "ACME",
            "model": "ST380815AS",
            "serialNumber": "2QZBZX1M",
            "size": 76319,
            "test": {
                "@type": "TestHardDrive",
                "error": false,
                "firstError": null,
                "lifetime": 0,
                "status": "Completed without error",
                "type": "Short offline"
            }
        },
        {
            "@type": "RamModule",
            "interface": "DDR",
            "manufacturer": "7F98000000000000",
            "serialNumber": "AB6F3B4D",
            "size": 512,
            "speed": 533.0
        },
        {
            "@type": "Motherboard",
            "connectors": {
                "firewire": 0,
                "pcmcia": 0,
                "serial": 0,
                "usb": 5
            },
            "manufacturer": "Acme Inc.",
            "model": "0RJ291",
            "serialNumber": "..NC317046CX01ZJ.",
            "totalSlots": 0,
            "usedSlots": 2
        },
        {
            "@type": "NetworkAdapter",
            "manufacturer": "ACME Corporation",
            "model": "NetXtreme BCM5751 Gigabit Ethernet PCI Express",
            "serialNumber": "00:11:22:33:44:55",
            "speed": 1000
        },
        {
            "@type": "OpticalDrive",
            "description": "DVD-RAM writer",
            "manufacturer": "HL-DT-ST",
            "model": "DVD-RAM GSA-H55N"
        },
        {
            "@type": "Processor",
            "benchmark": {
                "@type": "BenchmarkProcessor",
                "score": 3193.19
            },
            "manufacturer": "ACME Corp.",
            "model": "ACME(R) Pontium(R) D CPU 2.80GHz",
            "numberOfCores": 2,
            "serialNumber": "0000-0F47-0000-0000-0000-0000"
        },
        {
            "@type": "SoundCard",
            "manufacturer": "ACME Corporation",
            "model": "82801G (ICH7 Family) AC'97 Audio Controller"
        }
    ],
    "condition": {
        "appearance": {
            "general": "C"
        },
        "functionality": {
            "general": "B"
        }
    },
    "device": {
        "@type": "Computer",
        "manufacturer": "ACME Inc.",
        "model": "Super GX520",
        "serialNumber": "GTK1N3J",
        "type": "Desktop"
    },
    "label": "PC-7",
    "version": "8.0a2"
}
```

## Known limitations
- Unsupported USB network adaptors.
