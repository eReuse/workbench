# https://help.ubuntu.com/community/LiveCDCustomization


### Pre-requisites ###
sudo apt-get install squashfs-tools genisoimage
wget http://ubuntu-mini-remix.mirror.garr.it/mirrors/ubuntu-mini-remix/15.10/ubuntu-mini-remix-15.10-i386.iso -O base_image.iso

md5sum base_image.iso
# 78399fed67fc503d2f770f5ad7dcab45  ubuntu-mini-remix-15.10-i386.iso

### UNPACK the ISO ###

# Mount the base image .iso
mkdir -p mnt
sudo mount -o loop base_image.iso mnt

# Extract .iso contents into dir 'extract-cd'
mkdir -p extract-cd
sudo rsync --exclude=/casper/filesystem.squashfs -a mnt/ extract-cd

# Extract the SquashFS filesystem
sudo unsquashfs mnt/casper/filesystem.squashfs
sudo mv squashfs-root edit

### CUSTOMIZE IT ###
# Prepare chroot
sudo mount -o bind /run/ edit/run

# chroot
sudo mount --bind /dev/ edit/dev
sudo chroot edit
mount -t proc none /proc
mount -t sysfs none /sys
mount -t devpts none /dev/pts

# avoid local issues
export HOME=/root
export LC_ALL=C

# TODO manually update resolv.conf
rm /etc/resolv.conf
echo "nameserver  208.67.222.222" > /etc/resolv.conf

# Enable universe repository (/etc/apt/sources.list)
apt-get install -y software-properties-common
add-apt-repository "deb http://archive.ubuntu.com/ubuntu $(lsb_release -sc) universe"

# installation tools requirements (could be removed)
apt-get update
apt-get -y install git-core python-pip  # vim

# NOTE on ubuntu python-dev is required to install paramiko (pycrypto)
# device-inventory requirements
apt-get install -y lshw dmidecode python-dev python-dmidecode python-lxml smartmontools usbmount python-dateutil

# paramiko pyudev pySMART
pip install -r https://raw.githubusercontent.com/eReuse/device-inventory/master/device_inventory/requirements.txt

pip install --upgrade git+https://github.com/ereuse/device-inventory.git#egg=device_inventory

# Configure timezone
dpkg-reconfigure tzdata

# Generate and update default locale
locale-gen es_ES.UTF-8
update-locale LANG=es_ES.UTF-8 LANGUAGE=es_ES.UTF-8 LC_ALL=es_ES.UTF-8

# Set keyboard layout
dpkg-reconfigure keyboard-configuration

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#   UPC REUTILITZA - GRAPHICAL ENVIRONMENT     #
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#apt-get install xorg icewm

#~~~~~~~~~~~~~~~~ end UPC ~~~~~~~~~~~~~~~~~~~~~~

## CLEAN UP ##
## PURGE temporal packages XXX?
#apt-get purge git python-pip
apt-get clean

# If you installed software, be sure to run
rm /var/lib/dbus/machine-id
rm /sbin/initctl
dpkg-divert --rename --remove /sbin/initctl

# Add ubuntu user:
adduser ubuntu
# password: ubuntu

# Autologin
nano /etc/systemd/system/getty.target.wants/getty@tty1.service
# change the line for: ExecStart=/sbin/agetty --noclear --autologin ubuntu %I $TERM

# Autostart
echo "clear ; sudo device-inventory" >> /home/ubuntu/.profile

# delete temporary files
rm -rf /tmp/* ~/.bash_history

# now umount (unmount) special filesystems and exit chroot
umount /proc || umount -lf /proc
umount /sys
umount /dev/pts
exit
sudo umount edit/run
sudo umount edit/dev

### PACK the ISO ###

# Regenerate manifest
sudo chmod +w extract-cd/casper/filesystem.manifest
sudo chroot edit dpkg-query -W --showformat='${Package} ${Version}\n' | sudo tee extract-cd/casper/filesystem.manifest
sudo cp extract-cd/casper/filesystem.manifest extract-cd/casper/filesystem.manifest-desktop
sudo sed -i '/ubiquity/d' extract-cd/casper/filesystem.manifest-desktop
sudo sed -i '/casper/d' extract-cd/casper/filesystem.manifest-desktop

# remove previous squashfs
sudo rm -f extract-cd/casper/filesystem.squashfs

# highest compression (~3min) FIXME xz compression is not compatible
#sudo mksquashfs edit extract-cd/casper/filesystem.squashfs -comp xz -e edit/boot

# XXX NO COMPRESSION - DEBUG PURPOSES (~1min)
sudo mksquashfs edit extract-cd/casper/filesystem.squashfs -e edit/boot

# Update the filesystem.size file, which is needed by the installer:
printf $(sudo du -sx --block-size=1 edit | cut -f1) > extract-cd/casper/filesystem.size

# Set an image name in extract-cd/README.diskdefines
##sudo vim extract-cd/README.diskdefines

# Remove old md5sum.txt and calculate new md5 sums
cd extract-cd
sudo rm md5sum.txt
find -type f -print0 | sudo xargs -0 md5sum | grep -v isolinux/boot.cat | sudo tee md5sum.txt

# Create the ISO image
# A) Ubuntu
#sudo mkisofs -D -r -V "$IMAGE_NAME" -cache-inodes -J -l -b isolinux/isolinux.bin -c isolinux/boot.cat -no-emul-boot -boot-load-size 4 -boot-info-table -o ../eReuseOS_v7.0.2b.iso .

# B) Debian
sudo genisoimage -D -r -V "eReuseOS" -cache-inodes -J -l -b isolinux/isolinux.bin -c isolinux/boot.cat -no-emul-boot -boot-load-size 4 -boot-info-table -o ../eReuseOS_v7.0.2b.iso .

cd ..
