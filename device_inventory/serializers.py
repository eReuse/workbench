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


def dict_to_xml(equip, outfile="/tmp/equip.xml"):
    root = ConvertDictToXml(equip)
    indent(root)
    tree = ElementTree.ElementTree(root)
    tree.write(outfile)
