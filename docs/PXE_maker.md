![eReuselogo](./images/eReuse_logo_200.png)
![UPClogo](./images/UPC_logo_200.png)

#eReuse: How to make PXE server (Debian Server)

Guide version: 7.1.0a3

This guide will allow you to make a PXE server and boot computers via ethernet network.

####First steps, install debain server image:
1. You can find the newest stable Debian Server [here](http://debian.xfree.com.ar/debian-cd/current/amd64/iso-cd/)
  - Netinst mode recommended.
2. Download the latest release of eReuseOS image from [here](https://github.com/eReuse/device-inventory/releases/latest)
3. Download the installation ISO of the OS you want to install in clients (we will be using 32-bit Lubuntu from [here](http://cdimage.ubuntu.com/lubuntu/releases/16.04.1/release/) as an example, but any other 32-bit Ubuntu will do)

####Services 
On this guide, you will install the following services:

`DHCP`, `TFTP` and `NFS`.

####The network boot process is as follows:

- Clients receive DHCP network parameters: IP of BOOTP server that is serving network boot image and the name of the network image.
- Clients asks for the network image via TFTP, then load and run it.
- When network image starts to run, loads the kernel of the system and mount the filesystem via NFS.
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
wget https://github.com/eReuse/device-inventory/releases/download/v7.1.0a3/eReuseOS_v7.1.0a3.iso
wget http://cdimage.ubuntu.com/lubuntu/releases/16.04.1/release/lubuntu-16.04.1-desktop-i386.iso
wget -O /home/ereuse/config.ini https://raw.githubusercontent.com/eReuse/device-inventory/master/device_inventory/config.ini
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
/var/lib/tftpboot/mnt/Ubuntu_image *(no_root_squash,no_subtree_check,ro)
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
mv ~/eReuseOS_v7.1.0a3.iso iso
mv ~/lubuntu-16.04.1-desktop-i386.iso iso
```

Make the dir to mount the eReuseOS iso. These are the folders that will be shared on network:
```
mkdir mnt/eReuse_image/
mkdir mnt/Ubuntu_image/
```

Now edit `/etc/fstab` to mount it when server starts:
```
nano /etc/fstab
```

Add the lines:
```
/var/lib/tftpboot/iso/eReuseOS_v7.1.0a3.iso /var/lib/tftpboot/mnt/eReuse_image iso9660 ro 0 0
/var/lib/tftpboot/iso/lubuntu-16.04.1-desktop-i386.iso /var/lib/tftpboot/mnt/Ubuntu_image iso9660 ro,nofail 0 0
```

Test they are automounted with:
```
mount -a
ls -l mnt/eReuse_image/
ls -l mnt/Ubuntu_image/
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
        append boot=casper ip=dhcp netboot=nfs nfsroot=192.168.2.2:/var/lib/tftpboot/mnt/eReuse_image text forcepae
        IPAPPEND 2

LABEL Ubuntu
    MENU LABEL ^Ubuntu
        kernel mnt/Ubuntu_image/casper/vmlinuz
        initrd mnt/Ubuntu_image/casper/initrd.lz
        append boot=casper ip=dhcp netboot=nfs nfsroot=192.168.2.2:/var/lib/tftpboot/mnt/Ubuntu_image ksdevice=bootif ks=nfs:192.168.2.2:/var/lib/tftpboot/ks/ks.cfg forcepae quiet splash -- forcepae quiet splash
        IPAPPEND 2
```
