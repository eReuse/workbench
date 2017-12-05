# -*- coding: utf-8 -*-
# !/usr/bin/env python
import uuid
from time import sleep

from ereuse_utils.usb_flash_drive import plugged_usbs
from os.path import expanduser
from requests import Session


class USBSneaky(object):
    UUID_PATH = '{}/.eReuseUUID'.format(expanduser('~'))

    def __init__(self, workbench_server='https://192.168.2.2:8091'):
        self.UUID = self.uuid()
        self.workbench_server = workbench_server
        self.s = Session()
        self.s.verify = False
        print('Watching {} for {}'.format(uuid, workbench_server))
        while True:
            sleep(1.6)
            try:
                # We keep sending this so workbench server will notice our silence if we die and remove the USB
                # from its list of plugged in USBs
                pen = self.plugged_usb()
            except NoUSBFlashDriveFoundError:
                try:
                    print('Unplugged USB {}'.format(pen['_id']))
                    self.send_unplug(pen['hid'])  # Pen was defined, therefore we had a pen before
                    del pen  # We remove it so we are not sending it all the time to DeviceHub
                except NameError:
                    print('No previously plugged pen')
                    pass
            else:
                print('Plugged USB {}'.format(pen['_id']))
                # We have found an usb
                self.send_plug(pen)
                sleep(1)  # Don't stress Workbench Server

    def plugged_usb(self):
        try:
            pen = plugged_usbs()[0]
        except IndexError:
            raise NoUSBFlashDriveFoundError()
        else:
            pen['_uuid'] = self.UUID
            return pen

    @classmethod
    def uuid(cls):
        try:
            with open(cls.UUID_PATH, 'r') as f:
                device_uuid = f.read()
        except IOError:  # File not found
            device_uuid = uuid.uuid4().hex  # random UUID
            with open(cls.UUID_PATH, 'w') as f:
                f.write(device_uuid)
            print('UUID4: {}'.format(device_uuid))
        return device_uuid

    def send_plug(self, pen):
        # type: (dict) -> None
        self.s.post('{}/usbs/plugged/{}'.format(self.workbench_server, pen['hid']), json=pen)

    def send_unplug(self, hid):
        # type: (str) -> None
        self.s.delete('{}/usbs/plugged/{}'.format(self.workbench_server, hid))


class NoUSBFlashDriveFoundError(Exception):
    pass


if __name__ == "__main__":
    USBSneaky()
