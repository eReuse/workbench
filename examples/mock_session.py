import json
from pathlib import Path
from unittest.mock import MagicMock

import ereuse_utils

m = MagicMock()
counter = 0


def save(base_url: str, data, *args, **kwargs):
    if 'progress' in base_url:
        filename = '{} {} {}.json'.format(data['event'], data['component'], data['percentage'])
    elif kwargs.get('uri', None):
        filename = '{}.json'.format(str(kwargs['uri']).replace('/', '_'))
    else:
        filename = '{}.json'.format(base_url.replace('/', '_'))
    global counter
    counter += 1
    Path.home() \
        .joinpath(filename) \
        .write_text(json.dumps(data, cls=ereuse_utils.JSONEncoder))


m.post = save
m.patch = save
