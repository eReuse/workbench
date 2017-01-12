![eReuselogo](./images/eReuse_logo_200.png)
![UPClogo](./images/UPC_logo_200.png)

# eReuse: How to register via USB 

## 1. Download the eReuseOS image
 1. Go to [our repository](https://github.com/eReuse/workbench/releases/latest) and download the latest `ereuse-data-VERSION.tar.gz` archive.  Extract it somewhere in your computer.  In the `ereuse-data/images` directory you will find the `eReuseOS.iso` CD image.
 2. Install [UNetbootin](https://unetbootin.github.io/) software to make a live USB.
      - [Windows](https://launchpad.net/unetbootin/trunk/613/+download/unetbootin-windows-613.exe)
      - [Mac](https://launchpad.net/unetbootin/trunk/613/+download/unetbootin-mac-613.zip)
      - Ubuntu: open a terminal with `Ctrl+Alt+T` and execute `sudo apt-get update && sudo apt-get install unetbootin -y && unetbootin`

## 2. Create a bootable live USB with UNetbootin
*NOTE: it's recommended that the USB is blank before saving the image to it.*

 1. Select "Disk image".
 2. Select the `eReuseOS.iso` CD image file.
 3. Select the USB drive to write it to.
 4. Click *Ok* to start.

![](./images/UNetbootin_example.png)

## 3. Run eReuseOS
 1. Connect the USB drive with the eReuseOS image to the PC where you are going to register.
 2. Turn the PC on or reboot it, and configure the BIOS (the first few seconds when the PC starts) to boot from the USB drive:
      - Maybe there is an option to automatically boot from USB:
          - Watch for the BIOS Setup message.
          - Press F12, F8 or F9 to enter the boot menu.
      - Enter the BIOS Setup and change the boot priority:
          - Watch for the BIOS Setup message.
          - Press F2 or F10 to enter the BIOS setup.

## 4. Inventory process to register the hardware characteristics of a computer
 1. When the system starts, it will let you select the layout of your keyboard and then ask you some questions.

    **Note:** If you have a [PXE server](PXE_Register.md) on your LAN you may preconfigure the answers to some questions so that they are not asked and the process can move faster.

 2. You will need to answer to the following questions:
      - Label (optional): used to help identifying this PC among others registered in the same session, e.g. ``PC-1``, ``PC-2``, ``PC-3``...
      - Device type: choose what kind of equipment you are registering, i.e. a desktop, a laptop...
      - Visual grade (optional): evaluate the aesthetic condition of the device, i.e. new, used, worn, broken...
      - Functional grade (optional): evaluate the functional condition of the device, i.e. new, used, worn, broken...
      - Comment (optional): introduce any extra information that you deem necessary (e.g. describe if any peripheral equipment does not work).

 3. Wait until all the information from equipment is gathered.

 4. By default, a SMART check will start to execute (it takes 1 minute approximately).

 5. You will be asked if you want to perform a secure erase of each hard drive.  Please note that this can take **several hours**.

 6. (Optional) If a server is available, the system will try to upload the resulting JSON hardware description to it.

 7. You will be asked to insert another USB drive to store the result, just plug-in and wait until the result is saved or press `Ctrl+C` otherwise.

 8. You will be asked whether you want to install an operating system image.  To decline, press `Ctrl+C`.  Otherwise the installation will start for the prepared image that you choose from the ones that you have provided to the [PXE server](PXE_Register.md).

 9. The process is done! If you want to review the result, just open the file stored on the second USB (in this PC or another one, after shutting this one down), or run `less /tmp/NAME.json` on the inventoried device.  The exact name of the file is printed on the screen right after the *eReuse Workbench has finished properly* message (use `Tab` to complete the name on the command line).

    If you are not satisfied with the result and want to change some parameter, just type `exit` to repeat the process.

10. Power off the computer by pressing the power button or running `sudo poweroff`.  You may then unplug the USB drives.
