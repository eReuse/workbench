#!/bin/sh
# Configure this (virtual) host as an eReuse PXE server.
#
# This is meant to be run when generating the server OVA.

# Remove unnecessary packages.
apt-get -qq purge @PKGS_TO_REMOVE@

# Install needed packages.
# Enable additional packages like VirtualBox's.
sed -i -e 's/ main/ main multiverse/' /etc/apt/sources.list
apt-get update
apt-get -qq --no-install-recommends install virtualbox-guest-dkms

# Enable VirtualBox's shared folder module.
cat << 'EOF' > /etc/modules-load.d/ereuse
# To share eReuse's data folder with the VirtualBox host.
vboxsf
EOF

# Rebuild initramfs if missing.
if [ ! -f /initrd.img ]; then
    update-initramfs -u
fi

# Fix bootloader.
update-grub
grub-install $(findmnt -no SOURCE / | sed -r 's/p?[0-9]+$//')

# Setup users.
printf 'eReuse\neReuse\n' | passwd -q root
adduser --disabled-password --gecos eReuse ereuse
printf 'ereuse\nereuse\n' | passwd -q ereuse

# Cleanup.
apt-get clean  # downloaded package files

# Restore the original init script.
mv /etc/rc.local.orig /etc/rc.local

exec poweroff
