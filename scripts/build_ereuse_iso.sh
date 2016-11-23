#!/bin/sh

# https://help.ubuntu.com/community/LiveCDCustomization

set -e

VERSION=7.1a5
WORK_DIR="dist/iso"

BASE_ISO_URL="http://ubuntu-mini-remix.mirror.garr.it/mirrors/ubuntu-mini-remix/15.10/ubuntu-mini-remix-15.10-i386.iso"
BASE_ISO_MD5="78399fed67fc503d2f770f5ad7dcab45"
BASE_ISO_PATH=$WORK_DIR/$(basename "$BASE_ISO_URL")
BASE_ISO_MD5SUM="$BASE_ISO_MD5  $BASE_ISO_PATH"

ISO_PATH=$WORK_DIR/eReuseOS-$VERSION.iso

genisoimage --version > /dev/null  # fail if missing
mksquashfs -version > /dev/null  # fail if missing

mkdir -p $WORK_DIR

# Download the base ISO.
while ! echo "$BASE_ISO_MD5SUM" | md5sum -c --quiet --status; do
    wget -c -O $BASE_ISO_PATH "$BASE_ISO_URL"
done

# Mount a writable version of the ISO and the FS in it.
ISO_RO=$(mktemp -d -p$WORK_DIR)
ISO_RW_DATA=$(mktemp -d -p$WORK_DIR)
ISO_RW_WORK=$(mktemp -d -p$WORK_DIR)
ISO_ROOT=$(mktemp -d -p$WORK_DIR)

mount -t iso9660 -o loop,ro $BASE_ISO_PATH $ISO_RO
mount -t overlay -o lowerdir=$ISO_RO,upperdir=$ISO_RW_DATA,workdir=$ISO_RW_WORK base-iso $ISO_ROOT

FS_RO=$(mktemp -d -p$WORK_DIR)
FS_RW_DATA=$(mktemp -d -p$WORK_DIR)
FS_RW_WORK=$(mktemp -d -p$WORK_DIR)
FS_ROOT=$(mktemp -d -p$WORK_DIR)

mount -t squashfs -o loop,ro $ISO_RO/casper/filesystem.squashfs $FS_RO
mount -t overlay -o lowerdir=$FS_RO,upperdir=$FS_RW_DATA,workdir=$FS_RW_WORK ereuse $FS_ROOT

# To customize filesystem.
alias ch="chroot $FS_ROOT env HOME=/root LC_ALL=C"
alias chi="ch apt-get install -y --no-install-recommends"

# Customization prerequisites.
ch dbus-uuidgen > $FS_ROOT/var/lib/dbus/machine-id
ch dpkg-divert --local --rename --add /sbin/initctl
ch ln -s /bin/true /sbin/initctl

# Disable swapping to disk in a systemd-friendly way.
# See <https://tails.boum.org/contribute/design/#index34h3>.
ch dpkg-divert --rename --add /sbin/swapon
ch ln -s /bin/true /sbin/swapon

# TODO manually update resolv.conf
ch rm /etc/resolv.conf  # in case it's a link
echo "nameserver  208.67.222.222" > $FS_ROOT/etc/resolv.conf

# Enable universe repository (/etc/apt/sources.list)
chi software-properties-common
ch add-apt-repository "deb http://archive.ubuntu.com/ubuntu $(ch lsb_release -sc) universe"

# installation tools requirements (could be removed)
ch apt-get update
chi git-core python-pip  # vim

# device-inventory requirements
# TODO read from requirements.txt
chi $(sed -rn 's/.*\bdeb:(.+)$/\1/p' requirements.txt requirements-full.txt)

# Install Reciclanet's image installation script
ch wget "https://raw.githubusercontent.com/eReuse/SCRIPTS/ereuse/instalar" -O /usr/local/bin/di-install-image
ch chmod a+rx /usr/local/bin/di-install-image

ch pip install --upgrade "git+https://github.com/eReuse/device-inventory.git#egg=device_inventory"

# Configure regional settings
echo 'Etc/UTC' > $FS_ROOT/etc/timezone
ch debconf-set-selections << 'EOF'
locales locales/locales_to_be_generated multiselect es_ES.UTF-8 UTF-8
locales locales/default_environment_locale select es_ES.UTF-8
keyboard-configuration keyboard-configuration/layout select Spanish
keyboard-configuration keyboard-configuration/layoutcode select es
keyboard-configuration keyboard-configuration/variant select Spanish
EOF

ch dpkg-reconfigure -f noninteractive tzdata locales keyboard-configuration
ch locale-gen es_ES.UTF-8

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#   UPC REUTILITZA - GRAPHICAL ENVIRONMENT     #
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#ch apt-get install xorg icewm

#~~~~~~~~~~~~~~~~ end UPC ~~~~~~~~~~~~~~~~~~~~~~

## CLEAN UP ##
## PURGE temporal packages XXX?
#ch apt-get purge git python-pip
ch apt-get clean

# If you installed software, be sure to run
ch rm -f /var/lib/dbus/machine-id
ch rm -f /sbin/initctl
ch dpkg-divert --rename --remove /sbin/initctl

# Add ubuntu user:
printf 'ubuntu\nubuntu\n' | ch adduser -q --gecos 'Ubuntu' ubuntu

# Autologin
ch sed -i -r 's#(ExecStart=.*agetty )(.*)#\1--autologin ubuntu \2#' '/etc/systemd/system/getty.target.wants/getty@tty1.service'

# Autostart
echo "clear ; sudo device-inventory" >> $FS_ROOT/home/ubuntu/.profile

# delete temporary files
rm -rf $FS_ROOT/tmp/* $FS_ROOT/root/.bash_history

### PACK the ISO ###

# Regenerate manifest
ch dpkg-query -W --showformat='${Package} ${Version}\n' > $ISO_ROOT/casper/filesystem.manifest
cp $ISO_ROOT/casper/filesystem.manifest $ISO_ROOT/casper/filesystem.manifest-desktop
sed -i '/ubiquity/d' $ISO_ROOT/casper/filesystem.manifest-desktop
sed -i '/casper/d' $ISO_ROOT/casper/filesystem.manifest-desktop

# Create new squashfs using default compression, skip boot dir to save some space.
# LZMA is currently not supported even if the initramfs uses it for compression.
mksquashfs $FS_ROOT $ISO_ROOT/casper/filesystem-new.squashfs -e $FS_ROOT/boot

# replace squashfs
umount $FS_ROOT
umount $FS_RO
mv $ISO_ROOT/casper/filesystem-new.squashfs $ISO_ROOT/casper/filesystem.squashfs

# Update the filesystem.size file, which is needed by the installer:
mount -t squashfs -o loop,ro $ISO_ROOT/casper/filesystem.squashfs $FS_RO
printf $(sudo du -sx --block-size=1 $FS_RO | cut -f1) > $ISO_ROOT/casper/filesystem.size
umount $FS_RO

# Set an image name in extract-cd/README.diskdefines
##sudo vim extract-cd/README.diskdefines

# Calculate new SHA256 sums.
( cd $ISO_ROOT \
      && sed -i '/  \.\/casper\/filesystem\..*$/d' SHA256SUMS \
      && sha256sum ./casper/filesystem.* >> SHA256SUMS )

# Remove old md5sum.txt and calculate new md5 sums
( cd $ISO_ROOT \
     && rm -f md5sum.txt \
     && find -type f -print0 | xargs -0 md5sum | grep -v isolinux/boot.cat > md5sum.txt )

# Create the ISO image
# A) Ubuntu
#sudo mkisofs -D -r -V "$IMAGE_NAME" -cache-inodes -J -l -b isolinux/isolinux.bin -c isolinux/boot.cat -no-emul-boot -boot-load-size 4 -boot-info-table -o $ISO_PATH $ISO_ROOT

# B) Debian
genisoimage -D -r -V "eReuseOS" -cache-inodes -J -l -b isolinux/isolinux.bin -c isolinux/boot.cat -no-emul-boot -boot-load-size 4 -boot-info-table -o $ISO_PATH $ISO_ROOT

umount $ISO_ROOT

rm -rf $ISO_ROOT $ISO_WORK $ISO_DATA $ISO_RO $FS_ROOT $FS_WORK $FS_DATA $FS_RO

echo "Done, image created:" $ISO_PATH
