#!/usr/bin/env bash
# die on error, from https://stackoverflow.com/a/4346420
set -e
set -o pipefail

echo Execute with sudo!

# Where are the project files?
cd ${1:-'./..'}

echo Installing debian required packages...
cat debian-requirements.txt | xargs sudo apt install -y --no-install-recommends

echo Installing python packages...
pip install -e . -r requirements.txt

echo Installing erwb command line...
install -m 0755 scripts/erwb /usr/local/sbin/erwb
# Example: sudo erwb --settings /media/ereuse-data/config.ini --inventory /media/ereuse-data/inventory

echo Installing reciclanet scripts...
echo 'Ensure you have performed git submodule init / git submodule update'
#git submodule init
#git submodule update
install -m 0755 reciclanet-scripts/instalar /usr/local/bin/erwb-install-image

echo Workbench installed!
