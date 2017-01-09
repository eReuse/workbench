![eReuselogo](./images/eReuse_logo_200.png)
![UPClogo](./images/UPC_logo_200.png)

# eReuse: How to make PXE server (Debian Server)

Guide version: 8.0a1

This guide will allow you to configure an existing host as a PXE server and boot computers via an Ethernet network.  Please note that we strongly recommend using the [VirtualBox-based PXE server](PXE_Register.md) instead.

## The network boot process

- Clients receive DHCP network parameters: IP of BOOTP server that is serving network boot image and the name of the network image.
- Clients asks for the network image via TFTP, then load and run it.
- When network image starts to run, loads the kernel of the system and mount the filesystem via NFS.
- The diagnostic and inventory process takes place, and afterwards a system image may be installed to the computer via Samba.
- On reboot, the user can choose to run the installation ISO from the network.

## Configure your server
This assumes that the server's `eth0` interface is connected to the network where devices to be registered will be connected.  This should be different to the interface that the server uses to reach the Internet.

Download the latest eReuse *server configuration script*, *data refresh script* and *data archive*, along with optional *installation ISOs* (we will be using 32-bit Lubuntu here):
```
wget "https://raw.githubusercontent.com/eReuse/device-inventory/v8.0a1/scripts/configure-server.sh"
wget "https://raw.githubusercontent.com/eReuse/device-inventory/v8.0a1/scripts/ereuse-data-refresh"
wget "https://github.com/eReuse/device-inventory/releases/download/v8.0a1/ereuse-data-8.0a1.tar.gz"
wget "http://cdimage.ubuntu.com/lubuntu/releases/16.04.1/release/lubuntu-16.04.1-desktop-i386.iso"
```

Place the ``ereuse-data-refresh`` script under ``/usr/local/sbin``:
```
install -m 0755 ereuse-data-refresh /usr/local/sbin
```

### Network configuration

Edit the file `/etc/network/interfaces`:
```
nano /etc/network/interfaces
```

Then add or replace the following lines for the `eth0` interface:
```
auto eth0
iface eth0 inet static
    address         192.168.2.2
    netmask         255.255.255.0
    dns-nameservers 77.109.148.136 208.67.222.222 8.8.8.8
```

Reset network interfaces:
```
service networking restart
```

### Services configuration

Run the configuration script passing the name of the internal interface as an environment variable (other options are available, see the beginning of the script):
```
env INTERNAL_IFACE=eth0 ./configure-server.sh
```

This will install and configure all the needed packages, as well as create a dedicated user to host eReuse data.

You may need to manually tune the DCHP server configuration:
```
nano /etc/dhcp/dhcpd.conf
service isc-dhcp-server restart
```

### Data files

Unpack the data archive into `ereuse`'s home directory:
```
tar -xf ereuse-data-8.0a1.tar.gz
mv ereuse-data/* ~ereuse/data
```

If you want to use installation ISOs, place them in the `data/images` directory with names matching the existing `.syslinux` files:
```
cp lubuntu-16.04.1-desktop-i386.iso ~ereuse/data/images/Ubuntu32.iso
```

You may also copy any FSArchiver images to the same directory.

Then fix the ownership and permissions of the data files:
```
chown -R ereuse:ereuse ~ereuse/data
chmod -R a+rX ~ereuse/data
```

Whenever you drop new ISOs (and their associated SYSLINUX entry template files) in the `images` subdirectory of the data directory, please remember to run `ereuse-data-refresh` as root.
