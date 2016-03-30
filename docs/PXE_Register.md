![eReuselogo](./images/eReuse_logo_200.png)
![UPClogo](./images/UPC_logo_200.png)

# eReuse: How to use our (PXE) server

Guide version: 7.0.3

This server allow us to register easily and very fast by sending the image of the system to all PC 
connected on the LAN network.

#### To do a register we need the following needs

- A PC with:
  - [VirtualBox](https://www.virtualbox.org/wiki/Downloads)
  - [eReusePXE_CD-ROUTER.ova](https://github.com/eReuse/device-inventory/releases/latest)
  - [eReuseOS_vX.iso](https://github.com/eReuse/device-inventory/releases/latest)
- Switch
- Network cables
- PC/s to register

####Server info: 
- User: ereuse 
- Password: ereuse 
- IP of eReuse server: 192.168.2.2 
- Shared folder: 
  - Windows: `\\192.168.2.2\`
  - Linux: `smb://192.168.2.2/`

There is two network interfaces on the VirtualBox server.
  - eth0 (adapter 1): On “Bridged Adapter” on ethernet interface connected on the LAN with the other PCs to register.
  - eth1 (adapter 2): On “NAT” to connect on Internet from PC (if you have another interface with Internet like Wi­Fi).

####Steps to install and setup the server:
1. Install VirtualBox on any Win/Linux/Mac computer.
2. Double click on `eReusePXE_CD.ova` to import the server on VirtualBox.
3. Check the network configuration on VirtualBox.
  1. Adapter 1 should be on Ethernet (cable) interface with others computer (to be registed).
  2. Adapter 2 should be on NET if you have a second interface (from your second Ethernet or Wi-Fi interface)
4. Insert [eReuseOS_v7.0.3b6.iso](https://github.com/eReuse/device-inventory/releases/download/v7.0.3b6/eReuseOS_v7.0.3b6.iso) as CD media.
5. Run the virtual server and wait until system is loaded.
6. When the system asks for a login you can start to register computers.

####Configure ISO options
Info: The configuration file is called [config.ini](https://raw.githubusercontent.com/eReuse/device-inventory/master/device_inventory/config.ini).

1. On the server machine from VirtualBox, acces with the credentials.
2. write `nano /home/ereuse/config.ini`
3. Enable or disable all the options that you want.

####Steps to register a computer
1. Connect a PC to register on the LAN network.
2. Configure the BIOS (the first few seconds when computer starts) to boot LAN.
  1. Maybe there is a option to automatically boot from the network. 
    - Watch for the BIOS Setup Message. 
    - Press F12, F8 or F9 to enter on boot menu selection.
  2. Enter to Setup and change the boot priority.
    - Watch for the BIOS Setup Message.
    - Press F2 or F10 to enter on BIOS menu.
3. When the computer starts on LAN it will load the image from the server (can take 1 minute or more to load).

####More information
[Inventory process](https://github.com/eReuse/device-inventory/blob/master/docs/USB_Register.md#4-inventory-process-register-hardware-characteristics-of-a-computer)
