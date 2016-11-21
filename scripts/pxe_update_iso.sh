# Copy to the PXE Server
ISO="eReuseOS-7.1a5.iso"
scp $ISO xsr@192.168.2.2:/var/lib/tftpboot/iso/XSR_1.6-Desktop.iso

# Login and replace the old one with the new one
ssh xsr@192.168.2.2
sudo umount /var/lib/tftpboot/mnt/xsr_1.6-Desktop
sudo mount /var/lib/tftpboot/iso/XSR_1.6-Desktop.iso

# Test it
# - boot a host (e.g. another VM with an interface bridged to eth0)

# Clean up XMLs
#sudo rm ~tecnico/XMLs/*

# Clean up DHCPD leases
# /var/lib/dhcp/dhcpd.leases
