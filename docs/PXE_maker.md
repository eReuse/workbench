![eReuselogo](./images/eReuse_logo_200.png)
![UPClogo](./images/UPC_logo_200.png)

#eReuse: How to make PXE server (Debian Server)

Guide version: 8.0a1

This guide will allow you to make a PXE server and boot computers via ethernet network.

####First steps, install debain server image:
1. You can find the newest stable Debian Server [here](http://debian.xfree.com.ar/debian-cd/current/amd64/iso-cd/)
  - Netinst mode recommended.
2. Download the latest release of eReuseOS image from [here](https://github.com/eReuse/device-inventory/releases/latest)
3. Download the installation ISO of the OS you want to install in clients (we will be using 32-bit Lubuntu from [here](http://cdimage.ubuntu.com/lubuntu/releases/16.04.1/release/) as an example, but other distros are supported)
4. Download the FSArchiver images the OS you want to install in clients

####Services 
On this guide, you will install the following services:

DHCP, TFTP, NFS and Samba.

####The network boot process is as follows:

- Clients receive DHCP network parameters: IP of BOOTP server that is serving network boot image and the name of the network image.
- Clients asks for the network image via TFTP, then load and run it.
- When network image starts to run, loads the kernel of the system and mount the filesystem via NFS.
- The diagnostic and inventory process takes place, and afterwards a system image may be installed to the computer via Samba.
- On reboot, the user can choose to run the installation ISO from the network.

##Installation
####1. Install the services and get all files needed
Run the following command to intall TFTP services:
```
apt-get update
apt-get install tftpd-hpa isc-dhcp-server nfs-kernel-server
```

Place the ``ereuse-data-refresh`` under ``/usr/local/sbin`` and execute it at the end of ``/etc/rc.local``.

Download all files we need:
```
wget http://kaplah.org/system/files/field/files/pxelinux.tar.gz
wget https://github.com/eReuse/device-inventory/releases/download/v8.0a1/eReuseOS-8.0a1.iso
wget http://cdimage.ubuntu.com/lubuntu/releases/16.04.1/release/lubuntu-16.04.1-desktop-i386.iso
```

####2. Configure DHCP server
Install DHCP with a static IP on a supposed name interfice `eth0`.

Look for your ethernet interface name:
```
ip addr
```

If your name interface is not `eth0`, remplace it with your name interface.

Edit the file `/etc/network/interfaces`:
```
nano /etc/network/interfaces
```

And add or remplace the following lines for `eth0` interface:
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

See `man dhcpd` for more information. 
Make a backup of `/etc/dhcp/dhcpd.conf`:
```
mv /etc/dhcp/dhcpd.conf /etc/dhcp/dhcpd.conf.backup
```

Edit file with `nano /etc/dhcp/dhcpd.conf`:
```
nano /etc/dhcp/dhcpd.conf
```

And add the following lines:
```
ddns-update-style interim;
ignore client-updates;

# TFTP options
allow booting;
allow bootp;

# My network environment
subnet 192.168.2.0 netmask 255.255.255.0 {
 next-server 192.168.2.2;
 filename "pxelinux.0";
 range dynamic-bootp 192.168.2.10 192.168.2.210;
 option domain-name-servers 208.67.222.222;
 option routers 192.168.2.1;
 option broadcast-address 192.168.2.255;
}
```
Reset the service and check if service is running:
```
service isc-dhcp-server restart
```
If your `eth0` is on auto dhcp you will get an error. Uncomment and restart network interafes on static mode.

Test if service is running correctly:
```
ss -upna
tail /var/log/syslog
```

####3. Configure public access via SMB to data files

Create an ``ereuse`` user with a ``data`` directory in its home.  In it,
create subdirectories for ``images`` and the ``inventory`` of JSON files.
Download the ``config.ini`` into the ``data`` directory and copy FSArchiver
images to the ``images`` subdirectory, along with the ISO files that you
downloaded.  For backwards compatibility, you may create ``config.ini`` and
``inventory``  symbolic links to their counterparts under ``data``.  Change
the ownership of everything to the ``ereuse`` user:

```
adduser ereuse
mkdir -p ~ereuse/data/images ~ereuse/data/inventory
wget -O ~/ereuse/data/config.ini https://raw.githubusercontent.com/eReuse/device-inventory/master/device_inventory/config.ini
#(copy FSArchiver images to ``~ereuse/data/images``)#
mv ~/eReuseOS-8.0a1.iso ~ereuse/data/images/eReuseOS.iso
mv ~/lubuntu-16.04.1-desktop-i386.iso ~ereuse/data/images/Ubuntu32.iso
chown -R ereuse:ereuse ~ereuse/data
chmod -R a+rX ~ereuse/data
```

Create the ``/srv/ereuse-data`` directory and bind mount ``~ereuse/data``
there by adding this to ``/etc/fstab``:

```
/home/ereuse/data  /srv/ereuse-data  none  bind  0  0
```

Then mount it with ``mount -a``.

Install Samba with ``apt-get install samba`` and add the following share
definitions to ``/etc/samba/smb.conf`` to enable public read/write access to
eReuse data files:

```
[ereuse-data]
        comment = eReuse data
        path = /srv/ereuse-data
        browseable = yes
        read only = no
        guest ok = yes
        force user = ereuse
        force group = ereuse
```

Then reload the service with ``service samba reload``.

####4. Configure TFTP final step
Install the PXE network image from to `/var/lib/tftpboot/`:
```
cd /var/lib/tftpboot/
mv ~/pxelinux.tar.gz .
tar xzvf pxelinux.tar.gz
```

Make a backup of `/var/lib/tftpboot/pxelinux.cfg/default` and open it.
```
mv pxelinux.cfg/default pxelinux.cfg/default.backup
nano pxelinux.cfg/default
```

Add the following lines:
```
default eReuseOS
prompt 1
timeout 50

###eReuse###
```

####5. Updating configuration for new ISOs

Whenever you drop new ISOs (and their associated SYSLINUX entry template
files) in the ``images`` subdirectory of the data directory, please run
``ereuse-data-refresh`` as root.
