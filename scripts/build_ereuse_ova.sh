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
disk_loop=$(losetup -fP --show "$DISK_IMAGE")
mkfs.ext4 -q ${disk_loop}p1
mkswap ${disk_loop}p2

# Mount the ISO, the VM root and restore the system.
iso="$DATA_DIR/iso"
ROOT="$DATA_DIR/root"  # mounted VM root file system
mkdir -p "$iso" "$ROOT"
mount -o ro "$BASE_ISO_PATH" "$iso"
mount ${disk_loop}p1 "$ROOT"
# Copy ISO file system.
unsquashfs -d "$ROOT/SQUASH" "$iso/casper/filesystem.squashfs"
mv "$ROOT/SQUASH"/* "$ROOT"
rmdir "$ROOT/SQUASH"
# Restore kernel and initramfs, save for later VM boot.
cp "$iso/casper/vmlinuz" "$(readlink -f "$ROOT/vmlinuz")"
cp "$iso/casper/initrd.lz" "$(readlink -f "$ROOT/initrd.img")"
cp "$iso/casper/vmlinuz" "$iso/casper/initrd.lz" "$DATA_DIR"
# Save the list of unnecessary Casper packages.
PKGS_TO_REMOVE=$(cat "$iso/casper/filesystem.manifest-remove" | tr '\n' ' ')
umount "$iso"

# Drop the system configuration init script.
mv "$ROOT/etc/rc.local" "$ROOT/etc/rc.local.orig"
install -m 0644 "scripts/configure-server.sh" "$ROOT/etc/rc.local"
sed -i -e "s/@PKGS_TO_REMOVE@/$PKGS_TO_REMOVE/" "$ROOT/etc/rc.local"

chroot "$ROOT" /bin/bash

# Unmount the file system and release the loop device.
umount "$ROOT"
losetup -d $disk_loop
