# Device inventory

Device inventory is a set of tools and services to assist the preparation for reuse and traceability of digital devices (capture of hardware characteristics, hardware rating and testing and secure deletion of data).

## Features
- Run in an unattended way without the need for additional steps rather than powering up the computer.

- Provides signed documents for deletion of data, tests of operation,
hardware information and serial numbers for traceability.

- Only a few minutes required to register and select devices which reach user defined requirements (e.g. hard drive witouth faulty sectors, at least one NIC...).


## Requirements
* Python (2.7)
* lshw
* dmidecode
* smartmontools

## Installation
On a Debian based distribution using `apt`:

    apt-get install lshw dmidecode python-dmidecode python-lxml smartmontools

And then install `device_inventory` and its requirements using `pip`:

    pip install git+https://github.com/ereuse/device-inventory.git#egg=device_inventory

## Usage
Just run it as priviliged user and fill some information:

    $ sudo device-inventory
        Label ID: 7
        Comment: eReuse device inventory.
        Choose device type
        1. Desktop
        2. Laptop
        3. Netbook
        4. Server
        5. Microtower
        Type: 1
        Device Inventory has finished properly: /tmp/A1B2C3SN.json

Generated output example:
```json
{
    "@type": "Snapshot",
    "comment": "eReuse device inventory.",
    "components": [
        {
            "@type": "GraphicCard",
            "manufacturer": "Acme Corporation",
            "memory": 256.0,
            "model": "82945G/GZ Integrated Graphics Controller"
        },
        {
            "@type": "HardDrive",
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
    "device": {
        "@type": "Computer",
        "manufacturer": "ACME Inc.",
        "model": "Super GX520",
        "serialNumber": "GTK1N3J",
        "type": "Desktop"
    },
    "label": "7"
}
```

## Known limitations
- Unsupported USB network adaptors.
