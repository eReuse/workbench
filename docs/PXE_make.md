#eReuse: How to make PXE server (Debian Server)

This guide will allow you to make a PXE server and boot computers via ethernet network.

####First steps, install debain server image:
1. You can find the newest stable Debian Server [here](http://debian.xfree.com.ar/debian-cd/current/amd64/iso-cd/)
2. Download the netinst mode and install it on a real machine.
3. Download the latest release of eReuseOS image from [here](https://github.com/eReuse/device-inventory/releases/latest)

####Services that will be installed:

`DHCP`, `TFTP` and `NFS`.

####The network boot process is as follows:

- Clients receive DHCP network parameters, the IP of BOOTP server that is serving network boot image, and the name of the network image.
- Clients asks for the network image via TFTP, then load and run it.
- When network image starts to run, loads the kernel of the system and mount the filesystem via NFS.

##Installation
####1. Install the TFTP
Run the following command to intall TFTP services:
```
apt-get install tftpd-hpa
```

The configuration of file can be found on `/etc/default/tftpd-hpa`, edit this file:
```
nano /etc/default/tftpd-hpa
```

And add the following line to tell where the files will be placed:
```
TFTP_DIRECTORY="/var/lib/tftpboot
```

Now, reset the service with:
```
service tftpd-hpa restart
```

Check if service is running with:
```
ss -upna | grep tftp
```

####2. Install DHCP server
Install DHCP with a static IP on a supposed name interfice `eth0`.

First look what is the name of your ethernet interface:
```
ip addr
```
If your name interface is not `eth0`, remplace it with your name interface.

Edit the file `/etc/network/interfaces`:
```
nano /etc/network/interfaces
```
And add the following lines:
```
auto eth0
iface eth0 inet static
    address         192.168.2.2
    netmask         255.255.255.0
    gateway         192.168.2.1
    dns-nameservers 8.8.8.8
```
Test if it is working reseting it:
```
service networking restart
```

If is working correctly, install the DHCP:
```
apt-get install isc-dhcp-server
```
See `man dhcpd` for more information. 
Edit `/etc/dhcp/dhcpd.conf` and remove all remplacing with the next lines:
```
ddns-update-style interim;
ignore client-updates;

# TFTP options
allow booting;
allow bootp;

# My network environment
subnet 192.168.15.0 netmask 255.255.255.0 {
 next-server 192.168.15.2;
 filename "pxelinux.0";
 range dynamic-bootp 192.168.15.100 192.168.15.200;
 option domain-name-servers 8.8.8.8;
 option routers 192.168.15.1;
 option broadcast-address 192.168.15.255;
}
```
Reset the service and check if service is running:
```
service isc-dhcp-server restart
```
Test if service is running correctly:
```
ss -upna
tail /var/log/syslog
```
