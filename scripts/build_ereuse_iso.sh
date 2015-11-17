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
sudo genisoimage -D -r -V "$IMAGE_NAME" -cache-inodes -J -l -b isolinux/isolinux.bin -c isolinux/boot.cat -no-emul-boot -boot-load-size 4 -boot-info-table -o ../eReuseOS_v6.3.3_chk.iso .

cd ..

