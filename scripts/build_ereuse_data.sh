#!/bin/sh
# Create a data archive containing the latest configuration file and needed
# directories to be shared with the virtual PXE server.

set -e

VERSION=$(cd device_inventory && python -c 'from __init__ import get_version; print get_version()')

BUILD_DIR=$(mktemp -d)

mkdir -p $BUILD_DIR/ereuse-data/inventory $BUILD_DIR/ereuse-data/images
cp device_inventory/config.ini $BUILD_DIR/ereuse-data

IMAGE=eReuseOS
cp dist/iso/$IMAGE-$VERSION.iso $BUILD_DIR/ereuse-data/images/$IMAGE.iso
cat > $BUILD_DIR/ereuse-data/images/$IMAGE.iso.syslinux << EOF
LABEL $IMAGE
    MENU LABEL $IMAGE
        kernel mnt/$IMAGE/casper/vmlinuz
        initrd mnt/$IMAGE/casper/initrd.lz
        append ip=dhcp netboot=nfs nfsroot=@ADDRESS@:@TFTPBOOT@/mnt/$IMAGE boot=casper text forcepae
        IPAPPEND 2
EOF

chmod -R a+rX $BUILD_DIR

tar -zcf dist/ereuse-data-$VERSION.tar.gz -C $BUILD_DIR ereuse-data
rm -rf $BUILD_DIR
