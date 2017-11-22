#!/usr/bin/env bash

# Install as server client
# Execute this script to install a Workbench that will connect to a Workbench Server
# This script installs the bridge side from the Workbench to connect to a Workbench Server:
# - Installs Workbench per se, so you don't have to call `install.sh`
# - Installs the Workbench USB Sneaky service
# - Installs the `workbench-data` mounter service

set -e
set -o pipefail

echo Execute with sudo!

# Where are the project files?
cd ${1:-'./..'}
wpath=$(pwd)/erwb # We need absolute
USER='user'

# Where is redis?
redis='192.168.2.2:6379'
# Install autostart scripts?
autoStart=${2:-true}
echo autoStart

echo Executing normal install first...
bash scripts/install.sh '.'
echo Continuing installing server-client stuff...

echo Install and enable Workbench USB Sneaky...
cat > /etc/systemd/system/workbench-usb.service << EOF
[Unit]
Description=Workbench USB Sneaky
After=multi-user.target

[Service]
# Ubuntu/Debian convention:
Type=simple
ExecStart=/usr/bin/python ${wpath}/usb.py
User=${USER}
Group=${USER}

[Install]
WantedBy=multi-user.target
EOF
chmod 644 /etc/systemd/system/workbench-usb.service
systemctl enable workbench-usb.service

echo Install service to mount data-directory...

install -m 0755 scripts/workbench-data /usr/local/sbin/workbench-data
cat > /etc/systemd/system/workbench-data.service << EOF
[Unit]
Description=Workbench Data Mounter
After=multi-user.target

[Service]
# Ubuntu/Debian convention:
Type=oneshot
ExecStart=/usr/local/sbin/workbench-data

[Install]
WantedBy=multi-user.target
EOF
chmod 644 /etc/systemd/system/workbench-data.service
systemctl enable workbench-data.service

echo 'Done :-) Note that you need to start the new services: "workbench-usb.service" and "workbench-data.service".'
echo 'Example: sudo systemctl start workbench-usb'