# -*- coding: utf-8 -*-
# !/usr/bin/env python

from sys import argv

from os.path import exists, expanduser

from uuid import uuid4

import pyudev

from logging import getLogger
from logging.config import dictConfig

dict_config = {
    "version": 1,
    "formatters": {
        "standard": {
            "format": "%(asctime)s %(levelname)s %(module)s %(message)s"
        },
        "detailed": {
            "format": '%(asctime)s %(module)-17s line:%(lineno)-4d ' \
                      '%(levelname)-8s %(message)s'
        }
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "standard"
        },
        "file": {
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "detailed",
            "filename": "/tmp/sneaky.log",
            "mode": "a",
            "maxBytes": 10485760,
            "backupCount": 5
        }
    },
    "loggers": {
        "": {
            "handlers": ["console", "file"],
            "level": "DEBUG",
        }
    }
}

dictConfig(dict_config)

log = getLogger(__name__)


def read_uuid(path):
    if exists(path):
        with open(path, "r") as f:
            uuid = f.read()
    else:
        uuid = uuid4().hex
        with open(path, "w") as f:
            f.write(uuid)

    return uuid


def get_usb_stick_info(dev):
    return {
        "vendor": {"id": dev["ID_VENDOR_ID"], "name": dev["ID_VENDOR"]},
        "product": {
            "id": dev["ID_MODEL_ID"], "name": dev["ID_MODEL"], "serial": dev.get("ID_SERIAL_SHORT", "ID_SERIAL")
        }
    }


def push_to_server(action, url, uuid, info):
    if url.startswith("http"):
        import requests

        if action == "add":
            requests.get("{}/plug/{}/{}/{}/{}".format(url, info["product"]["serial"], uuid, info["vendor"]["name"],
                                                      info["product"]["name"]))
        else:
            requests.get("{}/unplug/{}/{}".format(url, info["product"]["serial"], uuid))
    else:
        from celery import Celery

        celery = Celery("workbench", broker=url)

        if action == "add":
            data = {
                "inventory": uuid, "vendor": info["vendor"]["name"], "product": info["product"]["name"],
                "usb": info["product"]["serial"]
            }
            celery.send_task("worker.add_usb", [data, ])
        else:
            data = {"inventory": uuid}
            celery.send_task("worker.add_usb", [data, ])


def sneak(url, uuid_path):
    uuid = read_uuid(uuid_path)
    log.info("Watching {} for {}".format(uuid, url))
    context = pyudev.Context()
    mon = pyudev.Monitor.from_netlink(context)
    mon.filter_by(subsystem="block")

    for action, dev in mon:
        if "ID_BUS" in dev and dev["ID_BUS"] == "usb" and dev["DEVTYPE"] == "disk":
            info = get_usb_stick_info(dev)
            if action == "add":
                log.info("Adds: {}".format(info))
                push_to_server("add", url, uuid, info)
                # requests.get("{}/plug/{}/{}/{}/{}".format(url, info["product"]["serial"], uuid, info["vendor"]["name"], info["product"]["name"]))
            elif action == "remove":
                log.info("Removes: {}".format(info))
                push_to_server("remove", url, uuid, info)
                # requests.get("{}/unplug/{}/{}".format(url, info["product"]["serial"], uuid))


if __name__ == "__main__":
    url = argv[1] if len(argv) > 1 else 'redis://192.168.2.2:6379/0'
    sneak(url, "{}/.eReuseUUID".format(expanduser("~")))
