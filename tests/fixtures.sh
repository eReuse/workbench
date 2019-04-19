#!/usr/bin/env bash
lshw -json > device.lshw.json
hwinfo --reallyall > device.hwinfo.txt
cat /sys/class/power_supply/BAT0/uevent > device.battery.txt
