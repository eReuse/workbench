#!/bin/sh
# Generate OVA of eReuse PXE server.

set -e

# Configurable settings.
WORK_DIR=${WORK_DIR:-dist/iso}
DISK_MiB=${DISK_MiB:-2048}  # VM disk size in MiB
SWAP_MiB=${SWAP_MiB:-128}  # VM swap size in MiB

BASE_ISO_URL="http://ubuntu-mini-remix.mirror.garr.it/mirrors/ubuntu-mini-remix/15.10/ubuntu-mini-remix-15.10-i386.iso"
BASE_ISO_SHA256="e9985f0bcb05678d87d62c3d70191aab7a80540dc17523d93c313aa8515e173e"

# Other derived values.
BASE_ISO_PATH="$WORK_DIR/$(basename "$BASE_ISO_URL")"
BASE_ISO_SHA256SUM="$BASE_ISO_SHA256  $BASE_ISO_PATH"


# Download the base ISO.
while ! echo "$BASE_ISO_SHA256SUM" | sha256sum -c --quiet --status; do
    wget -c -O $BASE_ISO_PATH "$BASE_ISO_URL"
done

# Create a temporary directory for data files.
DATA_DIR=$(mktemp -d -p"$WORK_DIR")

# Create and partition the VM disk image.
DISK_IMAGE="$DATA_DIR/disk.raw"  # VM disk image
dd if=/dev/zero "of=$DISK_IMAGE" bs=1M count=0 "seek=$DISK_MiB"  # sparse
swap_first_sector=$(((DISK_MiB - SWAP_MiB) * 1024 * 2))
default=  # just for readability
cat << EOF | tr ' ' '\n' | fdisk "$DISK_IMAGE" > /dev/null
n p 2 $swap_first_sector $default
n p 1 $default $default
t 2 82
w
EOF

# Create a file system and a swap space in the VM disk.
DISK_LOOP=$(losetup -fP --show "$DISK_IMAGE")  # loop device for VM disk
mkfs.ext4 -q -O ^metadata_csum ${DISK_LOOP}p1
mkswap ${DISK_LOOP}p2

# Mount the ISO, the VM root and restore the system.
iso="$DATA_DIR/iso"
ROOT="$DATA_DIR/root"  # mounted VM root file system
mkdir -p "$iso" "$ROOT"
mount -o ro "$BASE_ISO_PATH" "$iso"
mount ${DISK_LOOP}p1 "$ROOT"
# Copy ISO file system.
unsquashfs -d "$ROOT/SQUASH" "$iso/casper/filesystem.squashfs"
mv "$ROOT/SQUASH"/* "$ROOT"
rmdir "$ROOT/SQUASH"
# Restore kernel, save for later VM boot.
cp "$iso/casper/vmlinuz" "$(readlink -f "$ROOT/vmlinuz")"
cp "$iso/casper/vmlinuz" "$DATA_DIR"
# Save the list of unnecessary Casper packages.
PKGS_TO_REMOVE=$(cat "$iso/casper/filesystem.manifest-remove" | tr '\n' ' ')
umount "$iso"

# Other packages to remove.
PKGS_TO_REMOVE="$PKGS_TO_REMOVE thermald"
# Avoid attempting graphical login and get a console login prompt.
PKGS_TO_REMOVE="$PKGS_TO_REMOVE plymouth"
sed -i -e '/^GRUB_HIDDEN_/d' -e 's/quiet splash/quiet/' "$ROOT/etc/default/grub"

# Create a minimal fstab (mainly for the initramfs).
cat << 'EOF' > "$ROOT/etc/fstab"
/dev/sda1  /     ext4  relatime,errors=remount-ro  0  1
/dev/sda2  none  swap  sw                          0  0
EOF
# Network configuration.
cat << 'EOF' > "$ROOT/etc/network/interfaces.d/ereuse"
auto eth0
allow-hotplug eth0
iface eth0 inet static
	address  192.168.2.2
	netmask  255.255.255.0
	gateway  192.168.2.1
	dns-nameservers  8.8.8.8 8.8.4.4

auto eth1
allow-hotplug eth1
iface eth1 inet dhcp
EOF
echo eReuse > "$ROOT/etc/hostname"

# Drop the system configuration init script.
mv "$ROOT/etc/rc.local" "$ROOT/etc/rc.local.orig"
install -m 0755 "scripts/configure-server.sh" "$ROOT/etc/rc.local"
sed -i -e "s/@PKGS_TO_REMOVE@/$PKGS_TO_REMOVE/" "$ROOT/etc/rc.local"

chroot "$ROOT" /bin/bash

# Unmount the file system and release the loop device.
umount "$ROOT"
losetup -d $DISK_LOOP
