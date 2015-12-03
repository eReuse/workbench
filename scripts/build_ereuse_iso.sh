# https://help.ubuntu.com/community/LiveCDCustomization


### Pre-requisites ###
sudo apt-get install squashfs-tools genisoimage

### UNPACK the ISO ###

# Mount the base image .iso
mkdir mnt
sudo mount -o loop base_image.iso mnt

# Extract .iso contents into dir 'extract-cd'
mkdir extract-cd
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

# Enable universe repository (/etc/apt/sources.list)
apt-get install software-properties-common
add-apt-repository "deb http://archive.ubuntu.com/ubuntu $(lsb_release -sc) universe"

# installation tools requirements (could be removed)
apt-get update
apt-get install git python-pip

# NOTE on ubuntu python-dev is required to install paramiko (pycrypto)
# device-inventory requirements
apt-get install lshw dmidecode python-dmidecode python-lxml smartmontools
pip install paramiko

pip install --upgrade git+https://github.com/ereuse/device-inventory.git#egg=device_inventory

# FIXME config.ini not included ??
wget https://raw.githubusercontent.com/eReuse/device-inventory/master/device_inventory/config.ini -O /usr/local/lib/python2.7/dist-packages/device_inventory/config.ini
mkdir /usr/local/lib/python2.7/dist-packages/device_inventory/static/
wget https://github.com/eReuse/device-inventory/raw/master/device_inventory/static/meaningless_values.txt -O /usr/local/lib/python2.7/dist-packages/device_inventory/static/meaningless_values.txt

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
apt-get install xorg icewm

#~~~~~~~~~~~~~~~~ end UPC ~~~~~~~~~~~~~~~~~~~~~~

## CLEAN UP ##
## PURGE temporal packages XXX?
#apt-get purge git python-pip
apt-get clean

# If you installed software, be sure to run
rm /var/lib/dbus/machine-id
rm /sbin/initctl
dpkg-divert --rename --remove /sbin/initctl

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
sudo chroot edit dpkg-query -W --showformat='${Package} ${Version}\n' > extract-cd/casper/filesystem.manifest
sudo cp extract-cd/casper/filesystem.manifest extract-cd/casper/filesystem.manifest-desktop
sudo sed -i '/ubiquity/d' extract-cd/casper/filesystem.manifest-desktop
sudo sed -i '/casper/d' extract-cd/casper/filesystem.manifest-desktop

# remove previous squashfs
sudo rm extract-cd/casper/filesystem.squashfs

# highest compression (~3min)
sudo mksquashfs edit extract-cd/casper/filesystem.squashfs -comp xz -e edit/boot

# XXX NO COMPRESSION - DEBUG PURPOSES (~1min)
#sudo mksquashfs edit extract-cd/casper/filesystem.squashfs -e edit/boot

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
#sudo mkisofs -D -r -V "$IMAGE_NAME" -cache-inodes -J -l -b isolinux/isolinux.bin -c isolinux/boot.cat -no-emul-boot -boot-load-size 4 -boot-info-table -o ../eReuseOS_v6.3.2.iso .

# B) Debian
sudo genisoimage -D -r -V "$IMAGE_NAME" -cache-inodes -J -l -b isolinux/isolinux.bin -c isolinux/boot.cat -no-emul-boot -boot-load-size 4 -boot-info-table -o ../eReuseOS_v7.0.iso .

cd ..

