#!/bin/sh
# Generate OVA of eReuse PXE server.

set -e

# Configurable settings.
DIST_DIR=${DIST_DIR:-dist}
DISK_MiB=${DISK_MiB:-2048}  # VM disk size in MiB
SWAP_MiB=${SWAP_MiB:-128}  # VM swap size in MiB
MEM_MiB=${MEM_MiB:-1024}  # VM memory size in MiB
ADDRESS=${ADDRESS:-192.168.2.2}  # VM internal IP address (/24)

# Version-specific settings.
VERSION=$(cd ereuse_ddi && python -Bc 'from __init__ import get_version; print get_version()')
BASE_ISO_URL="http://ubuntu-mini-remix.mirror.garr.it/mirrors/ubuntu-mini-remix/15.10/ubuntu-mini-remix-15.10-i386.iso"
BASE_ISO_SHA256="e9985f0bcb05678d87d62c3d70191aab7a80540dc17523d93c313aa8515e173e"

# Other derived values.
VBOX_NAME=ereuse-server-$VERSION
VBOX_OVA="$DIST_DIR/$VBOX_NAME.ova"
BASE_ISO_PATH="$DIST_DIR/iso/$(basename "$BASE_ISO_URL")"
BASE_ISO_SHA256SUM="$BASE_ISO_SHA256  $BASE_ISO_PATH"

if [ -f "$VBOX_OVA" ]; then
        echo "OVA already exists: $VBOX_OVA" >&2
        exit 1
fi

# Check existence of non-essential tools.
for prog in wget fdisk losetup mkfs.ext4 mkswap unsquashfs tune2fs swaplabel kvm zerofree VBoxManage; do
    if ! type $prog > /dev/null; then
        echo "Missing program: $prog" >&2
        exit 1
    fi
done


# Download the base ISO.
while ! echo "$BASE_ISO_SHA256SUM" | sha256sum -c --quiet --status; do
    wget -c -O $BASE_ISO_PATH "$BASE_ISO_URL"
done

# Create a temporary directory for data files.
DATA_DIR=$(mktemp -d -p"$DIST_DIR")

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
CASPER_PKGS=$(cat "$iso/casper/filesystem.manifest-remove" | tr '\n' ' ')
umount "$iso"

# Create a minimal fstab (mainly for the initramfs).
root_uuid=$(tune2fs -l ${DISK_LOOP}p1 | grep UUID | sed -rn 's/.*:\s*(.+)/\1/p')
swap_uuid=$(swaplabel ${DISK_LOOP}p2 | grep UUID | sed -rn 's/.*:\s*(.+)/\1/p')
cat << EOF > "$ROOT/etc/fstab"
UUID=$root_uuid  /     ext4  relatime,errors=remount-ro  0  1
UUID=$swap_uuid  none  swap  sw                          0  0
EOF
# Network configuration, using fixed interface names.
sed -i -re 's/^(GRUB_CMDLINE_LINUX)="(.*)"/\1="\2 net.ifnames=0"/' "$ROOT/etc/default/grub"
cat << EOF > "$ROOT/etc/network/interfaces.d/ereuse"
# The internal, isolated network for serving client devices.
auto eth0
allow-hotplug eth0
iface eth0 inet static
	address  $ADDRESS
	netmask  255.255.255.0
	dns-nameservers  77.109.148.136 208.67.222.222 8.8.8.8

# The external network to reach the Internet.
auto eth1
allow-hotplug eth1
iface eth1 inet dhcp
EOF
echo eReuse > "$ROOT/etc/hostname"
# Install the data refresh script.
install -m 0755 "scripts/ereuse-data-refresh" "$ROOT/usr/local/sbin"

# Drop the system configuration init script.
mv "$ROOT/etc/rc.local" "$ROOT/etc/rc.local.orig"
install -m 0755 "scripts/configure-server.sh" "$ROOT/etc/rc.local"
sed -i -e "s/@CASPER_PKGS@/$CASPER_PKGS/" "$ROOT/etc/rc.local"

# Unmount the file system and release the loop device.
umount "$ROOT"
losetup -d $DISK_LOOP

# Run under KVM/QEMU once to complete configuration.
kvm -curses -m $MEM_MiB -drive file="$DISK_IMAGE",format=raw,if=virtio \
    -net user -net nic,model=virtio -net user -net nic,model=virtio \
    -kernel "$DATA_DIR/vmlinuz" -append "root=/dev/vda1 rw quiet"

# Use zerofree to zero unused blocks and ease compression.
DISK_LOOP=$(losetup -fP --show "$DISK_IMAGE")
zerofree ${DISK_LOOP}p1
losetup -d $DISK_LOOP

# Create the VirtualBox VM.
vbox_net=eth0
vbox_disk=$(realpath "${DISK_IMAGE%.raw}.vmdk")  # asbolute path
VBoxManage internalcommands createrawvmdk \
           -filename "$vbox_disk" -rawdisk "$(realpath "$DISK_IMAGE")"
VBoxManage createvm --name $VBOX_NAME --ostype Ubuntu --register
VBoxManage modifyvm $VBOX_NAME --memory $MEM_MiB \
           --acpi on --pae on --hpet on --apic on --hwvirtex on --ioapic off \
           --rtcuseutc on --firmware bios --vram 1 \
           --nic1 bridged --nictype1 virtio --bridgeadapter1 $vbox_net \
           --nic2 nat --nictype2 virtio \
           --audio none --usb off --clipboard disabled --draganddrop disabled
VBoxManage storagectl $VBOX_NAME \
           --name "SATA" --add sata --portcount 1 --bootable on
VBoxManage storageattach $VBOX_NAME \
           --storagectl "SATA" --port 0 --device 0 --type hdd --medium "$vbox_disk"
VBoxManage sharedfolder add $VBOX_NAME \
           --name ereuse-data --hostpath /path/of/ereuse-data

# Export the VBox VM.
VBoxManage export $VBOX_NAME -o "$VBOX_OVA" --vsys 0 \
           --product "eReuse PXE server" \
           --vendor "eReuse" --vendorurl "https://ereuse.org/" \
           --version $VERSION --description "\
IMPORTANT:
Remember to point the \"ereuse-data\" shared folder to
the directory extracted from the \"ereuse-data-VERSION.tar.gz\" archive:
https://github.com/eReuse/ddi/releases
--------------------------------
Access to shared folder via SMB:
- GNU/Linux: smb://$ADDRESS/
- Windows: \\\\$ADDRESS\\
--------------------------------
IP network: $ADDRESS/24
--------------------------------
User: ereuse
Password: ereuse
--------------------------------
Root pasword: eReuse
--------------------------------
"
chmod a+r "$VBOX_OVA"

# Cleanup.
VBoxManage unregistervm $VBOX_NAME --delete
rm -rf "$DATA_DIR"

echo "Successfully built OVA: $VBOX_OVA"
