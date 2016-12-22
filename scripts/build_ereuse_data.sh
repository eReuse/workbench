#!/bin/sh
# Create a data archive containing the latest configuration file and needed
# directories to be shared with the virtual PXE server.

set -e

VERSION=$(cd device_inventory && python -c 'from __init__ import get_version; print get_version()')

BUILD_DIR=$(mktemp -d)

mkdir -p $BUILD_DIR/ereuse-data/inventory $BUILD_DIR/ereuse-data/images
cp device_inventory/config.ini $BUILD_DIR/ereuse-data
cp dist/iso/eReuseOS-$VERSION.iso $BUILD_DIR/ereuse-data/images/eReuseOS.iso
for slconf in scripts/syslinux/*.iso.syslinux; do
    name=$(basename "$slconf" | sed 's/\.iso.syslinux$//')
    sed "s/@NAME@/$name/g" "$slconf" > $BUILD_DIR/ereuse-data/images/$(basename "$slconf")
done

chmod -R a+rX $BUILD_DIR

tar -zcf dist/ereuse-data-$VERSION.tar.gz -C $BUILD_DIR ereuse-data
rm -rf $BUILD_DIR
