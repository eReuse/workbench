import lxml

from . import get_version, utils


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
            comp_data = utils.strip_null_or_empty_values(item.__dict__)
            comp_data.update({"@type": type(item).__name__})
            components.append(comp_data)
    
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
        "version": get_version(),
    }
    
    # Include user's custom fields (e.g. label, comment)
    snapshot.update(user_input)
    # Move visual and functional state to a more structured format.
    state = {}
    for state_name in ['visual', 'functional']:
        state_value = snapshot.pop(state_name + '_state')
        if state_value:
            state[state_name] = {'general': state_value}
    if state:
        snapshot['state'] = state
    
    # Include full output (debugging purposes)
    if debug:
        snapshot['debug'] = {
            "lshw": lxml.etree.tostring(device.lshw_xml),
            "dmi": device.dmi,
            #'smart": ,
        }
    
    return snapshot
