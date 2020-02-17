# -*- coding: utf-8 -*-
# !/usr/bin/env python
from contextlib import suppress
from time import sleep
from uuid import UUID

import urllib3
from boltons import urlutils
from colorama import Fore
from ereuse_utils.session import DevicehubClient
from ereuse_utils.usb_flash_drive import NoUSBFound, UsbDoesNotHaveHid, plugged_usbs


class USBSneaky:
    """
    Detects plugged-in USBs, gets its info and sends it to a
    WorkbenchServer.

    USBSneaky is constantly sending the info about the USB it has
    plugged-in and notifies if it is has been removed. If USBSneaky
    doesn't update in some time WorkbenchServer will interpret the
    silence as the computer is off and then, unplug the USB. This
    is done because the computer can die or be shut down in any moment.

    USBSneaky is thought to be executed as a worker in a single process.
    """

    def __init__(self, uuid: UUID, workbench_server: str):
        self.session = DevicehubClient(urlutils.URL(workbench_server))
        self.session.verify = False
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        while True:
            sleep(1)
            try:
                # We keep sending this so workbench server will
                # notice our silence if we die and remove the USB
                # from its list of plugged in USBs
                pen = plugged_usbs(multiple=False)
            except NoUSBFound:
                with suppress(NameError):
                    # Pen was defined, therefore we had a pen before
                    self.send_unplug(pen['hid'])
                    # We remove it so we are not sending it all the time
                    del pen
            except UsbDoesNotHaveHid:
                print('{}USB incompatible (No S/N available). Please use another one.'
                      .format(Fore.YELLOW))
                sleep(3)
            else:
                # We have found an usb
                pen['uuid'] = uuid
                self.send_plug(pen)
                sleep(2.25)  # Don't stress Workbench Server

    def send_plug(self, pen: dict):
        self.session.post('/usbs/', pen, uri=pen['hid'], status=204)

    def send_unplug(self, hid: str):
        self.session.delete('/usbs/', uri=hid)
