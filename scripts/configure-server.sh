#!/bin/sh
# Configure this (virtual) host as an eReuse PXE server.
#
# This is meant to be run when generating the server OVA.

# Remove unnecessary packages.
apt-get -qq purge @PKGS_TO_REMOVE@ thermald plymouth

# Install needed packages.
# Enable additional packages like VirtualBox's.
sed -i -e 's/ main/ main multiverse/' /etc/apt/sources.list
apt-get -qq update
apt-get -qq --no-install-recommends install virtualbox-guest-dkms

# Enable VirtualBox's shared folder module.
cat << 'EOF' > /etc/modules-load.d/ereuse.conf
# To share eReuse's data folder with the VirtualBox host.
vboxsf
EOF

# Rebuild initramfs if missing.
if [ ! -f /initrd.img ]; then
    update-initramfs -u
fi

# Avoid attempting graphical login and get a console login prompt.
sed -i -r -e 's/^(GRUB_HIDDEN_.*)/#\1/' -e 's/quiet splash/quiet/' /etc/default/grub
# Fix boot loader.
update-grub
grub-install $(findmnt -no SOURCE / | sed -r 's/p?[0-9]+$//')

# Setup users.
printf 'eReuse\neReuse\n' | passwd -q root
adduser --disabled-password --gecos eReuse ereuse
printf 'ereuse\nereuse\n' | passwd -q ereuse

# Prepare the shared data directory.
mkdir -m 0755 ~ereuse/data
ln -s data/config.ini data/inventory ~ereuse  # compat links
chown -R ereuse:ereuse ~ereuse
mkdir -p /srv/ereuse-data
cat << 'EOF' >> /etc/fstab
# Mount the VirtualBox shared folder, then bind it to the usual place.
ereuse-data        /home/ereuse/data  vboxsf  rw,uid=ereuse,gid=ereuse,dmode=755,fmode=644  0  0
/home/ereuse/data  /srv/ereuse-data   none    bind  0  0
EOF

# Cleanup.
apt-get clean  # downloaded package files

# Restore the original init script.
mv /etc/rc.local.orig /etc/rc.local

exec poweroff
