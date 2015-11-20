import multiprocessing

from xml.etree import ElementTree

from .xml2dict import ConvertDictToXml


# http://stackoverflow.com/a/4590052/1538221
def indent(elem, level=0):
    i = "\n" + level*"\t"
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i


def dict_to_xml(equip, outfile):
    root = ConvertDictToXml(equip)
    indent(root)
    tree = ElementTree.ElementTree(root)
    tree.write(outfile)


def export_to_legacy_schema(device, status, beg_donator_time, end_donator_time):
    cpu = {
        'nom_cpu': device.processor.model,
        'fab_cpu': device.processor.manufacturer,
        'speed_cpu': device.processor.speed,
        'unit_speed_cpu': device.processor.SPEED_UNIT,
        'number_cpu': multiprocessing.cpu_count(),  ## device.processor.number_cpus,
        'number_cores': device.processor.numberOfCores,
        'score_cpu': device.processor.score,
    }
    ram = {
        'size_ram': device.memory.size,
        'unit_size': device.memory.CAPACITY_UNIT,
        'interface_ram': device.memory.interface,
        'free_slots_ram': device.memory.free_slots,
        'used_slots_ram': device.memory.used_slots,
        'score_ram': device.memory.score,
    }
    hdd = {
        "model": device.hard_disk.model,
        "serial": device.hard_disk.serial,
        "size": device.hard_disk.size,
        "measure": device.hard_disk.CAPACITY_UNITS,
        "name": device.hard_disk.logical_name,
        "interface": device.hard_disk.interface,
    }
    vga = {
        "model_vga": "{0} {1}".format(device.graphic_card.manufacturer, device.graphic_card.model),
        "size_vga": device.graphic_card.memory,
        "unit_size_vga": device.graphic_card.CAPACITY_UNITS,
        "score_vga": device.graphic_card.score,
    }
    audio = [{"model_audio": card.model} for card in device.sound_cards]
    network = [
        {"model_net": iface.model, "speed_net": iface.speed_net,}
        for iface in device.network_interfaces
    ]
    optical_drives = [
        {"model_uni": drive.model, "tipo_uni": drive.description,}
        for drive in device.optical_drives
    ]
    connectors = [
        {"connector":
            {"tipus_connector": c.verbose_name, "nombre_connector": c.count,}
        }
        for c in device.motherboard.connectors if c.count > 0
    ]
    brand_info = {
        "fab_marca": device.manufacturer,
        "model_marca": device.model,
    }
    computer = {
        "equip": {
            "id": device.ID,
            "id2": device.ID2,
            "ID_donant": "",
            "ID_2": "",
            "LABEL": "",
            "INITIAL_TIME": "0",
            "INITIAL_DONATOR_TIME": beg_donator_time,
            "comments": "some comment",
            "type": "1",
            "serials": {
                "serial_fab": device.serialNumber,
                "serial_mot": device.motherboard.serialNumber,
                "serial_cpu": device.processor.serialNumber,
                "serial_ram": device.memory.serialNumber,
                "serial_hdd": device.hard_disk.serialNumber,
            },
            "estat": status,
            "caracteristiques": {
                "cpu": cpu,
                "ram": ram,
                "hdd": hdd,
                "vga": vga,
                "audio": audio,
                "net": network,
                "unidad": optical_drives,
                "connectors": connectors,
                "marca": brand_info,
            },
            "END_DONATOR_TIME": end_donator_time,
        }
    }
    
    return computer


"""
# Class > dict > JSON
import json
from device_inventory import inventory

dev = inventory.Computer()
processor = inventory.Processor(dev.lshw_json)
json.dumps(processor.__dict__)

"""
def export_to_devicehub_schema(device):
    components = []
    for cp_name in ["processor", "memory", "hard_disk", "graphic_card",
                    "motherboard", "network_interfaces", "optical_drives"]:
        cp = getattr(device, cp_name)
        
        # We could receive an array of components (e.g. HDDs)
        if hasattr(cp, '__iter__'):
            for item in cp:
                value = item.__dict__
                value.update({"@type": type(item).__name__})
                components.append(item.__dict__)
        
        # Or only a component (e.g. motherboard)
        else:
            value = cp.__dict__
            value.update({"@type": type(cp).__name__})
            components.append(cp.__dict__)
    
    snapshot = {
        "@type": "Snapshot",
        "device": {
            "@type": type(device).__name__,
            "type": device.type,
            "label": "",  # TODO ask user
            "manufacturer": device.manufacturer,
            "model": device.model,
            "serialNumber": device.serialNumber,
            "totalMemory": device.memory.size,
        },
        "components": components,
    }
    
    return snapshot
