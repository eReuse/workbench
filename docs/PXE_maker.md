![eReuselogo](./images/eReuse_logo_200.png)
![UPClogo](./images/UPC_logo_200.png)

#eReuse: How to make PXE server (Debian Server)

Guide version: 7.1a8

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

Download all files we need:
```
wget http://kaplah.org/system/files/field/files/pxelinux.tar.gz
wget https://github.com/eReuse/device-inventory/releases/download/v7.1a8/eReuseOS-7.1a8.iso
wget http://cdimage.ubuntu.com/lubuntu/releases/16.04.1/release/lubuntu-16.04.1-desktop-i386.iso
```

####2. Configure TFTP


The configuration can be found on `/etc/default/tftpd-hpa`, edit this file:
```
nano /etc/default/tftpd-hpa
```

Change the following line to tell where the files will be placed:
```
TFTP_DIRECTORY="/var/lib/tftpboot"
```

Make the folder:
```
mkdir /var/lib/tftpboot
```

Reset the service with:
```
service tftpd-hpa restart
```

Check if service is running:
```
ss -upna | grep tftp
```

####3. Configure DHCP server
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
    gateway         192.168.2.1
    dns-nameservers 208.67.222.222
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
####4. Configure NFS
Edit `/etc/exports`:
```
nano /etc/exports
```

Add the following lines:
```
/var/lib/tftpboot/ks *(no_root_squash,no_subtree_check,ro)
/var/lib/tftpboot/mnt/eReuse_image *(no_root_squash,no_subtree_check,ro)
/var/lib/tftpboot/mnt/inst_media *(no_root_squash,no_subtree_check,ro)
```

####5. Configure TFTP final step
Install the PXE network image from to `/var/lib/tftpboot/`:
```
cd /var/lib/tftpboot/
mv ~/pxelinux.tar.gz .
tar xzvf pxelinux.tar.gz
```

Make all the folders that we will use for the configuration:
```
mkdir iso mnt ks
```

Move the isos to `/var/lib/tftpboot/iso`:
```
mv ~/eReuseOS-7.1a8.iso iso
mv ~/lubuntu-16.04.1-desktop-i386.iso iso
```

Make the dir to mount the eReuseOS iso. These are the folders that will be shared on network:
```
mkdir mnt/eReuse_image/
mkdir mnt/inst_media/
```

Now edit `/etc/fstab` to mount it when server starts:
```
nano /etc/fstab
```

Add the lines:
```
/var/lib/tftpboot/iso/eReuseOS-7.1a8.iso /var/lib/tftpboot/mnt/eReuse_image iso9660 ro 0 0
/var/lib/tftpboot/iso/lubuntu-16.04.1-desktop-i386.iso /var/lib/tftpboot/mnt/inst_media iso9660 ro,nofail 0 0
```

Test that they are automounted with:
```
mount -a
ls -l mnt/eReuse_image/
ls -l mnt/inst_media/
```

Reload NFS service:
```
service nfs-kernel-server restart
```

Check if is mounted on network:
```
showmount -e 192.168.2.2
```

Make a backup of `/var/lib/tftpboot/pxelinux.cfg/default` and open it.
```
mv pxelinux.cfg/default pxelinux.cfg/default.backup
nano pxelinux.cfg/default
```

Add the following lines:
```
default eReuse
prompt 1
timeout 50

LABEL eReuse
    MENU LABEL eReuse
        kernel mnt/eReuse_image/casper/vmlinuz
        initrd mnt/eReuse_image/casper/initrd.lz
        append ip=dhcp netboot=nfs nfsroot=192.168.2.2:/var/lib/tftpboot/mnt/eReuse_image boot=casper text forcepae
        IPAPPEND 2

LABEL ChaletOS32
    MENU LABEL ChaletOS32
        kernel mnt/inst_media/casper/vmlinuz
        initrd mnt/inst_media/casper/initrd.gz
        append ip=dhcp netboot=nfs nfsroot=192.168.2.2:/var/lib/tftpboot/mnt/inst_media ksdevice=bootif quiet splash boot=casper forcepae
        IPAPPEND 2

LABEL ChaletOS64
    MENU LABEL ChaletOS64
        kernel mnt/inst_media/casper/vmlinuz
        initrd mnt/inst_media/casper/initrd.gz
        append ip=dhcp netboot=nfs nfsroot=192.168.2.2:/var/lib/tftpboot/mnt/inst_media ksdevice=bootif quiet splash boot=casper
        IPAPPEND 2

LABEL DebianLive32
    MENU LABEL DebianLive32
        kernel mnt/inst_media/live/vmlinuz2
        initrd mnt/inst_media/live/initrd2.img
        append ip=dhcp netboot=nfs nfsroot=192.168.2.2:/var/lib/tftpboot/mnt/inst_media ksdevice=bootif quiet splash boot=live components forcepae
        IPAPPEND 2

LABEL DebianLive64
    MENU LABEL DebianLive64
        kernel mnt/inst_media/live/vmlinuz
        initrd mnt/inst_media/live/initrd.img
        append ip=dhcp netboot=nfs nfsroot=192.168.2.2:/var/lib/tftpboot/mnt/inst_media ksdevice=bootif quiet splash boot=live components forcepae
        IPAPPEND 2

LABEL Ubuntu32
    MENU LABEL Ubuntu32
        kernel mnt/inst_media/casper/vmlinuz
        initrd mnt/inst_media/casper/initrd.lz
        append ip=dhcp netboot=nfs nfsroot=192.168.2.2:/var/lib/tftpboot/mnt/inst_media ksdevice=bootif quiet splash boot=casper forcepae
        IPAPPEND 2

LABEL Ubuntu64
    MENU LABEL Ubuntu64
        kernel mnt/inst_media/casper/vmlinuz.efi
        initrd mnt/inst_media/casper/initrd.lz
        append ip=dhcp netboot=nfs nfsroot=192.168.2.2:/var/lib/tftpboot/mnt/inst_media ksdevice=bootif quiet splash boot=casper
        IPAPPEND 2
```

####5. Configure public access via SMB to TFTP inventory files

Create an ``ereuse`` user with ``adduser ereuse``.  Download the
``config.ini`` file to its home directory:

```
wget -O /home/ereuse/config.ini https://raw.githubusercontent.com/eReuse/device-inventory/master/device_inventory/config.ini
```

Create the ``/srv/ereuse-data`` directory, copy FSArchiver images to its
``images`` subdirectory, and change its ownership to the ``ereuse`` user that
you just created:

```
mkdir -p /srv/ereuse-data
mkdir /srv/ereuse-data/images
#(copy FSArchiver images to ``/srv/ereuse-data/images``)#
chown -R ereuse:ereuse /srv/ereuse-data
chmod -R a+rX /srv/ereuse-data
```

Install Samba with ``apt-get install samba`` and add the following share
definitions to ``/etc/samba/smb.conf`` to enable public read/write access to
inventory files and read access to image files:

```
[eReuse Inventory]
        comment = eReuse Inventory
        path = /home/ereuse/inventory
        browseable = yes
        read only = no
        guest ok = yes

[ereuse-data]
        comment = eReuse data
        path = /srv/ereuse-data
        browseable = yes
        read only = yes
        guest ok = yes
```

Then reload the service with ``service samba reload``.
