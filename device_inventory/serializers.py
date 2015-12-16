import lxml
import multiprocessing

from xml.etree import ElementTree

from . import utils
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
    processor = device.processor[0]
    hard_disk = device.hard_disk[0]
    graphic_card = device.graphic_card[0]
    memory = device.memory[0]
    
    cpu = {
        'nom_cpu': processor.model,
        'fab_cpu': processor.manufacturer,
        'speed_cpu': processor.speed,
        'unit_speed_cpu': processor.SPEED_UNIT,
        'number_cpu': multiprocessing.cpu_count(),  ## device.processor.number_cpus,
        'number_cores': processor.numberOfCores,
        'score_cpu': processor.score,
    }
    ram = {
        'size_ram': memory.size,
        'unit_size_ram': memory.CAPACITY_UNIT,
        'interface_ram': memory.interface,
        'free_slot_ram': device.motherboard.freeSlots,
        'used_slot_ram': device.motherboard.usedSlots,
        'score_ram': None,  # device.memory.score,
    }
    hdd = {
        "model": hard_disk.model,
        "serial": hard_disk.serialNumber,
        "size": hard_disk.size,
        "measure": hard_disk.CAPACITY_UNITS,
        "name": '/dev/sda',  # TODO hard_disk.logical_name,
        "interface": hard_disk.interface,
    }
    vga = {
        "model_vga": "{0} {1}".format(graphic_card.manufacturer, graphic_card.model),
        "size_vga": graphic_card.memory,
        "unit_size_vga": graphic_card.CAPACITY_UNITS,
        "score_vga": graphic_card.score,
    }
    audio = [{"model_audio": card.model} for card in device.sound_cards]
    network = [
        {"model_net": iface.model, "speed_net": iface.speed,}
        for iface in device.network_interfaces
    ]
    optical_drives = [
        {"model_uni": drive.model, "tipo_uni": drive.description,}
        for drive in device.optical_drives
    ]
    C_VERBOSE = dict((key, value) for value, key in device.motherboard.CONNECTORS)
    connectors = [
        {"connector":
            {"tipus_connector": C_VERBOSE[value], "nombre_connector": count,}
        }
        for value, count in device.motherboard.connectors.items() if count > 0
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
                "serial_cpu": processor.serialNumber,
                "serial_ram": memory.serialNumber,
                "serial_hdd": hard_disk.serialNumber,
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
def export_to_devicehub_schema(device, user_input=None, debug=False):
    if user_input is None:
        user_input = {}
    
    components = []
    for comp_name in device.COMPONENTS:
        comp = getattr(device, comp_name)
        
        # We could receive an array of components (e.g. HDDs)
        # Or only a component (e.g. motherboard)
        if not hasattr(comp, '__iter__'):
            comp = [comp]
        
        for item in comp:
            value = item.__dict__
            value.update({"@type": type(item).__name__})
            components.append(utils.strip_null_or_empty_values(item.__dict__))
    
    device_serialized = utils.strip_null_or_empty_values({
        "@type": type(device).__name__,
        "type": device.type,
        "manufacturer": device.manufacturer,
        "model": device.model,
        "serialNumber": device.serialNumber,
    })
    
    snapshot = {
        "@type": "Snapshot",
        "device": device_serialized,
        "components": components,
    }
    
    # Include user's custom fields (e.g. label, comment)
    snapshot.update(user_input)
    
    # Include full output (debugging purposes)
    if debug:
        snapshot['debug'] = {
            "lshw": lxml.etree.tostring(device.lshw_xml),
            "dmi": device.dmi,
            #'smart": ,
        }
    
    return snapshot
