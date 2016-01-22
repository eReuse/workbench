![eReuselogo](./images/eReuse_logo_200.png)
![UPClogo](./images/UPC_logo_200.png)

#eReuse: How to make PXE server (Debian Server)

This guide will allow you to make a PXE server and boot computers via ethernet network.

####First steps, install debain server image:
1. You can find the newest stable Debian Server [here](http://debian.xfree.com.ar/debian-cd/current/amd64/iso-cd/)
  - Download the netinst mode and install it on a real machine.
2. Download the latest release of eReuseOS image from [here](https://github.com/eReuse/device-inventory/releases/latest)

####Services 
On this guide, you will install the following services:

`DHCP`, `TFTP` and `NFS`.

####The network boot process is as follows:

- Clients receive DHCP network parameters: IP of BOOTP server that is serving network boot image and the name of the network image.
- Clients asks for the network image via TFTP, then load and run it.
- When network image starts to run, loads the kernel of the system and mount the filesystem via NFS.

##Installation
####1. Install the TFTP
Run the following command to intall TFTP services:
```
apt-get update
apt-get install tftpd-hpa
```

The configuration can be found on `/etc/default/tftpd-hpa`, edit this file:
```
nano /etc/default/tftpd-hpa
```

Add or change the following line to tell where the files will be placed and create the folder:
```
TFTP_DIRECTORY="/var/lib/tftpboot"
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

####2. Install DHCP server
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
    dns-nameservers 8.8.8.8
```

if you need eth0 on auto dhcp mode to acces on internet, just comment the following lines and uncomment when you finished the installation. Exemple:
```
auto eth0
iface eth0 inet dhcp
#static
#    address         192.168.2.2
#    netmask         255.255.255.0
#    gateway         192.168.2.1
#    dns-nameservers 8.8.8.8
```


Reset network interfaces:
```
service networking restart
```

Install the DHCP service:
```
apt-get install isc-dhcp-server
```

See `man dhcpd` for more information. 
Make a backup of `/etc/dhcp/dhcpd.conf`:
```
mv /etc/dhcp/dhcpd.conf /etc/dhcp/dhcpd.conf.backup
```

Edit file with `nano /etc/dhcp/dhcpd.conf` and add the following lines:
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
##3. Install NFS
NFS will allow us to share network images. Install it with:
```
apt-get install nfs-kernel-server
```

Edit `/etc/exports` with the folders that we will use, add:
```
/var/lib/tftpboot/ks *(no_root_squash,no_subtree_check,ro)
/var/lib/tftpboot/mnt/eReuseOS_iso *(no_root_squash,no_subtree_check,ro)
```

##4. install TFTP
Install the PXE network image from to `/var/lib/tftpboot/`:
```
cd /var/lib/tftpboot/
wget http://kaplah.org/system/files/field/files/pxelinux.tar.gz
tar xzvf pxelinux.tar.gz
```

Make all the folders that we will use for the configuration:
```
mkdir /var/lib/tftpboot/iso
mkdir /var/lib/tftpboot/mnt
mkdir /var/lib/tftpboot/ks
```

Get the latest iso from our github [releases](https://github.com/eReuse/device-inventory/releases/latest), copy the link of the newest ISO and donwload it with:
```
wget -O /var/lib/tftpboot/iso https://github.com/eReuse/device-inventory/releases/download/v7.0.2b/eReuseOS_v7.0.2b.iso
```

Make the dir to mount the eReuseOS iso. This is the folder that will be shared on network:
```
mkdir /var/lib/tftpboot/mnt/eReuseOS_iso/
```

Now edit `/etc/fstab` to mount it when server starts:
```
sudo nano /etc/fstab
```

Add the line:
```
/var/lib/tftpboot/eReuseOS_v7.0.2b.iso /var/lib/tftpboot/mnt/eReuseOS_iso iso9660 user,ro,loop 0 0
```

Test if is automounted with:
```
mount -a
ls -l /var/lib/tftpboot/mnt/eReuseOS_iso/
```

Reload NFS service:
```
service nfs-kernel-server reload
```

Check if is mounted on network:
```
showmount -e 192.168.15.2
```

Make a backup of `/var/lib/tftpboot/pxelinux.cfg/default` and open it.
```
mv /var/lib/tftpboot/pxelinux.cfg/default /var/lib/tftpboot/pxelinux.cfg/default.backup
nano /var/lib/tftpboot/pxelinux.cfg/default
```

Add the following lines:
```
default eReuseOS
prompt 0

LABEL eReuseOS
    MENU LABEL eReuseOS
        kernel mnt/eReuseOS_iso/casper/vmlinuz
        append file=mnt/eReuseOS_iso/preseed/ubuntu.seed intrd=mnt/eReuse_image/casper/initrd.lz boot=casper netboot=nfs ip=dhcp nfsroot=192.168.2.2:/var/lib/tftpboot/mnt/eReuse_image
```
####5. Finish
If you changed your interfaces to dhcp mode, turn it to static, edit `/etc/network/interfaces` to:
```
auto eth0
iface eth0 inet static
    address         192.168.2.2
    netmask         255.255.255.0
    gateway         192.168.2.1
    dns-nameservers 8.8.8.8
```

Test connecting a computer on the same network as the sever and seleect network boot.
