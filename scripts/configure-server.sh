#!/bin/sh
# Configure this (virtual) host as an eReuse PXE server.
#
# This is meant to be run as ``/etc/rc.local`` when generating the server OVA,
# then it takes over the whole host.
#
# The script also has some limited support for running it on an existing host:
# it just adds the needed configuration.  See the environment variables below
# for customization.  You may also need to manually tune the DCHP server
# configuration under ``/etc/dhcp/dhcpd.conf``.

# Configurable settings.
INTERNAL_IFACE=${INTERNAL_IFACE:-eth0}  # where registered devices will be
DATA_USER=${DATA_USER:-ereuse}  # same name for group
DATA_USER_PASS=${DATA_USER_PASS:-ereuse}  # created anew
ROOT_PASS=${ROOT_PASS:-eReuse}  # only for VM


if [ "$0" = /etc/rc.local ]; then
    vm=yes  # take full control of virtual host
else
    vm=no  # just add eReuse configuration
fi

# Remove unnecessary packages.
if [ $vm = yes ]; then
    apt-get -qq purge @CASPER_PKGS@ thermald plymouth
fi

# Install needed packages.
# Update 2017-05-05 -> Added git
pkgs_to_install="
    isc-dhcp-server tftpd-hpa pxelinux syslinux-common
    nfs-kernel-server samba git python-pip python-dev redis-server"
if [ $vm = yes ]; then
    # Enable VirtualBox's packages.
    sed -i -e 's/ main/ main multiverse/' /etc/apt/sources.list
    sed -i -e 's/ main/ main universe/' /etc/apt/sources.list
    pkgs_to_install="$pkgs_to_install virtualbox-guest-dkms"
fi
apt-get -qq update
apt-get -qq --no-install-recommends install $pkgs_to_install

# Enable VirtualBox's shared folder module.
if [ $vm = yes ]; then
    cat << 'EOF' > /etc/modules-load.d/ereuse.conf
# To share eReuse's data folder with the VirtualBox host.
vboxsf
EOF
fi

# Configure the DHCP server.
address=$(ip -4 addr show dev "$INTERNAL_IFACE" | sed -nr 's/.*\binet ([^/]+).*/\1/p')
netpfx24=$(echo $address | cut -f1-3 -d.)  # assume /24
nameservers=$(sed -rn 's/.*nameserver\s+([.0-9]+).*/\1/p' /etc/resolv.conf)
mv /etc/dhcp/dhcpd.conf /etc/dhcp/dhcpd.conf.backup
cat << EOF > /etc/dhcp/dhcpd.conf
ddns-update-style interim;
ignore client-updates;

# TFTP options
allow booting;
allow bootp;

# My network environment
subnet $netpfx24.0 netmask 255.255.255.0 {
  next-server $address;
  filename "pxelinux.0";
  range dynamic-bootp $netpfx24.10 $netpfx24.210;
  option domain-name-servers $(echo $nameservers | sed 's/ /, /g');
  option routers $address;
  option broadcast-address $netpfx24.255;
}
EOF
if [ $vm = no ]; then
    service isc-dhcp-server restart
fi

# Configure the Samba server.
cat << EOF >> /etc/samba/smb.conf
# eReuse shared data directory.
[ereuse-data]
   comment = eReuse data
   path = /srv/ereuse-data
   browseable = yes
   read only = no
   guest ok = yes
   force user = $DATA_USER
   force group = $DATA_USER
EOF
if [ $vm = no ]; then
    service samba restart
fi

# Configure PXE boot with TFTP.
sed -i -e 's/\[::\]//' /etc/default/tftpd-hpa  # Ubuntu bug #1448500
ln /usr/lib/PXELINUX/pxelinux.0 \
   /usr/lib/syslinux/modules/bios/menu.c32 \
   /usr/lib/syslinux/modules/bios/libutil.c32 \
   /usr/lib/syslinux/modules/bios/ldlinux.c32 \
   /var/lib/tftpboot
mkdir -p /var/lib/tftpboot/pxelinux.cfg
if [ $vm = no ]; then
    service tftpd-hpa restart
fi

# Configure boot.
if [ $vm = yes ]; then
    # Rebuild initramfs if missing.
    if [ ! -f /initrd.img ]; then
        update-initramfs -u
    fi

    # Avoid attempting graphical login and get a console login prompt.
    # Also, shorten menu timeout.
    sed -i -r -e 's/^(GRUB_HIDDEN_.*)/#\1/' -e 's/quiet splash/quiet/' \
        -e 's/^(GRUB_TIMEOUT)=.*/\1=3/' /etc/default/grub
    # Fix boot loader.
    update-grub
    grub-install $(findmnt -no SOURCE / | sed -r 's/p?[0-9]+$//')
fi

# Setup users.
if [ $vm = yes ]; then
    printf "$ROOT_PASS\n$ROOT_PASS\n" | passwd -q root
fi
adduser --disabled-password --gecos eReuse "$DATA_USER"
printf "$DATA_USER_PASS\n$DATA_USER_PASS\n" | passwd -q "$DATA_USER"

# Prepare the shared data directory.
data_user_home=$(getent passwd "$DATA_USER" | cut -d: -f6)
mkdir -m 0755 "$data_user_home/data"
ln -s data/config.ini data/inventory "$data_user_home"  # compat links
chown -R "$DATA_USER:$DATA_USER" "$data_user_home"
mkdir -p /srv/ereuse-data
if [ $vm = yes ]; then
    cat << EOF >> /etc/fstab
# Mount the VirtualBox shared folder as the data directory.
ereuse-data        $data_user_home/data  vboxsf  rw,uid=$DATA_USER,gid=$DATA_USER,dmode=755,fmode=644  0  0
EOF
fi
cat << EOF >> /etc/fstab
# Bind the data directory to the usual place.
$data_user_home/data  /srv/ereuse-data   none    bind  0  0
EOF
if [ $vm = no ]; then
    mount -a
fi

# get the Celery server
git clone https://github.com/eReuse/ACeleryWB.git $data_user_home/ACeleryWB
pip install -r $data_user_home/ACeleryWB/requirements.txt

# Celery worker
cat > /etc/systemd/system/ACeleryWBWorkers.service << EOF
[Unit]
Description=A Celery for Workbench
After=multi-user.target

[Service]
Type=simple
ExecStart=/usr/local/bin/celery worker -A worker --loglevel=info
User=$DATA_USER
Group=$DATA_USER

[Install]
WantedBy=multi-user.target
EOF
chmod 644 /etc/systemd/systemd/ACeleryWBWorkers.service
systemctl daemon-reload
systemctl enable ACeleryWBWorkers.service

# GUI
cat > /etc/systemd/system/WorkbenchGUI.service << EOF
[Unit]
Description=The GUI for Workbench
After=multi-user.target

[Service]
Type=simple
ExecStart=/usr/bin/python $data_user_home/ACeleryWB/webservice/app.py
User=$DATA_USER
Group=$DATA_USER

[Install]
WantedBy=multi-user.target
EOF
chmod 644 /etc/systemd/systemd/WorkbenchGUI.service
systemctl daemon-reload
systemctl enable WorkbenchGUI.service

# Cleanup and restore the original init script.
if [ $vm = yes ]; then
    apt-get clean  # downloaded package files
    mv /etc/rc.local.orig /etc/rc.local
fi

# Enable running the data refresh script during boot.
sed -i -re 's/^(exit 0.*)/ereuse-data-refresh\n\1/' /etc/rc.local
if [ $vm = no ]; then
    if ! ereuse-data-refresh; then
        echo 'Please install and run the ``ereuse-data-refresh`` script.' >&2
    fi
fi

# Halt the virtual machine.
if [ $vm = yes ]; then
    exec poweroff
fi
