![eReuselogo](./images/eReuse_logo_200.png)
![UPClogo](./images/UPC_logo_200.png)

# Options for "config.ini"

Guide version: 7.0.3  

This guide will explain you every option in config.ini file.  


## DEFAULT options

- EQUIP = **X**
    
This option allows you to automatically select the computers that you are going to register.  
Remplace X for:  
**Desktop**  
**Laptop**  
**Netbook**  
**Server**  
**Microtower**  
**(other)** = Ask  
  
- PID = **X**  
  
This options will enable the field PID. By default is set to `no`.  
Remplace X for:  
**yes** = ask for PID  
**no** = don't ask for PID  
  
- _ID = **X**  
  
This options will enable the field _ID. By default is set to `no`.  
Remplace X for:  
**yes** = ask for _ID  
**no** = don't ask for _ID  
  

- TIME = **X**  
  
To know how much time need the PC to do a complete register, you should insert here the time when system starts to load. By default is set to `no`.  
Remplace X for:  
**yes** = ask for TIME  
no = don't ask for TIME  
  

- LABEL = **X**
   
LABEL is used to enumerate or identify the computer that you are registering. By default is set to `yes`.  
Remplace X for:  
**yes** = ask for LABEL  
**no** = don't ask for LABEL  
  
- COMMENT = **X**  
  
Used for describe if computer have something in bad state or send some message to the receiver. By default is set to `yes`.  
Remplace X for:  
**yes** = ask for LABEL  
**no** = don't ask for  
  
- VISUAL_STATE = **X**
    
This option allows you to automatically indicate the aesthetic condition of the computers that you are going to register.  
Remplace X for:  
**A** = Brand new device  
**B** = Used, but no aesthetic defects  
**C** = Light aesthetic defects (scratches, dents, decoloration)  
**D** = Serious aesthetic defects (cracked covers, broken parts)  
**(other)** = Ask  
  
- OFFLINE = **X**  *(Not implemented)*  
  
This option allow to upload the inventory to the web server automatically. By default is set to `yes`.  
Remplace X for:  
**yes** = do not upload  
**no** = upload to web server  

- COPY_TO_USB = **X**  
  
Copy the inventory file (json) to USB when process is finished. It will wait until USB is detected to copy. By default is set to `yes`.  
Remplace X for:  
**yes** = try to copy to usb when is finished  
**no** = don't try to copy to USB  
  
- SENDTOSERVER = **X**  
  
Send the inventory file (json) to [eReusePXE Server](https://github.com/eReuse/device-inventory/blob/master/docs/PXE_Register.md) if is on LAN. By default is set to `yes`.  
Remplace X for:  
**yes** = send to server  
**no** = don't send to server  
  
- SMART = **X**  
  
Enable SMART test with specific option. By default is set to `short`.  
Remplace X for:  
**none** = don't do a SMART check  
**short** = do a short SMART on hard drive *(this process takes one minute approximately)*  
**long** = do a long SMART on hard drive *(this process takes 70 minutes approximately)*  
  
DEBUG = **X**  
  
Add full log of hardware to inventory (json) file for a better debugging. Default is set to `no`.  
Remplace X for:  
**yes** = add full information  
**no** = don't add full information  
  
## ERASER options
  
Options for erasure process.  
  
- MODE = **X**  
  
There is two available options to do a erase, both are a secure erase "bit per bit". By default is set to `EraseBasic`.  
Remplace X for:  
**EraseBasic** = fast erasure "bit per bit"  
**EraseSectors** = more secure erase with a validation of every sector erased  
  
- ERASE = **X**  
  
Options to ask or not to do an erasure. By default is set to `ask`.  
Remplace X for:   
**ask** =  ask to the user if want to do a erasure  
**yes** = do a erase without asking, will wait 10 seconds before erase start  
**no** = don't do or ask to do a erase  
  
- STEPS = **X**  
  
Choose how many steps you want to erase the hard drive. This process takes 1 hour and 30 minutes to erase 300 GB.  
Remplace X for the **number of steps you want to erase**. By default is set to `1`.  
  
- ZEROS = **X**
  
Add a final overwrite with zeros to hide shredding. By default is set to `False`.  
**True** = do a final overwrite with zeros  
**False** = Don't do a final overwrite with zeros  
  
## DONATOR options  
Still in development.  
  
## SERVER options  
  
Options to personalize the access to PXE server or a another server.  
    
- USERNAME = **X**  
  
Username of the user in the server to acces via SSH. json will be upload with this user.  
Remplace X for the **name of the user**. By default is `ereuse`.
  
- PASSWORD = **X**  
  
Remplace X for the **password** for the ssh user. By default is `ereuse`.  
  
- ADDRESS =  **X**  
  
IP address to access the PXE server. By default is `192.168.2.2`.  
  
- REMOTEPATH = **X**  
  
Remplace X for the **path to folder** where the json will be stored.  By default, the path is `/home/ereuse/inventory/`.  
  
## SIGNATURE option  
  
SIGN_OUTPUT = **X**  
  
Sign the json to avoid modifications. Device will generate two versions, one signed and another unsigned.  
If "COPY_TO_USB" option is enabled, only signed version will be moved to USB.  By default is set to `yes`.  
Remplace X for:  
**yes** = sign the json  
**no** = don't sign the json  

