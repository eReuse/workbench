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
        'nom_cpu': device.processor.product,
        'fab_cpu': device.processor.vendor,
        'speed_cpu': device.processor.freq,
        'unit_speed_cpu': device.processor.FREQ_UNIT,
        'number_cpu': device.processor.number_cpus,
        'number_cores': device.processor.number_cores,
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
        "model_vga": device.graphic_card.model,
        "size_vga": device.graphic_card.size,
        "unit_size_vga": device.graphic_card.CAPACITY_UNITS,
        "score_vga": device.graphic_card.score,
    }
    audio = [{"model_audio": card.product} for card in device.sound_cards]
    network = [
        {"model_net": iface.product, "speed_net": iface.speed_net,}
        for iface in device.network_interfaces
    ]
    optical_drives = [
        {"model_uni": drive.product, "tipo_uni": drive.description,}
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
        "model_marca": device.product,
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
            "serials": device.serials,
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
