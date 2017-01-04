#!/bin/sh
# Configure this (virtual) host as an eReuse PXE server.
#
# This is meant to be run when generating the server OVA.

# Remove unnecessary packages.
apt-get -qq purge @PKGS_TO_REMOVE@

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

# Restore the original init script.
mv /etc/rc.local.orig /etc/rc.local

exec poweroff
