import subprocess
import time
from datetime import datetime, timezone

import click
import ntplib
import requests
from boltons import urlutils
from colorama import Fore, Style
from ereuse_utils import cli
from ereuse_utils.session import Session

from ereuse_workbench.erase import EraseType
from ereuse_workbench.snapshot import Snapshot
from ereuse_workbench.test import TestDataStorageLength
from ereuse_workbench.workbench import Workbench

EPILOG = """\b
Ex. sudo erwb --benchmark --smart Short --erase EraseSectors --json out.json

will generate a hardware report plus benchmarks, a short SMART
test of all data storage units, and a certified erasure of all data
storage units, saving the resulting report as 'out.json'.
"""


@click.command(help=Workbench.__doc__, epilog=EPILOG)
@click.option('--benchmark/--no-benchmark', '-b',
              default=False,
              help='Benchmark the components using sysbench and other tools.')
@click.option('--smart', '-st',
              type=cli.Enum(TestDataStorageLength),
              help='Perform a SMART test to all the data storage units.')
@click.option('--erase', '-e', type=cli.Enum(EraseType), help='Erase all data storage units.')
@click.option('--erase-steps', '-es',
              type=click.IntRange(min=1),
              default=1,
              help='Number of erasure STEPS.')
@click.option('--erase-leading-zeros/--no-erase-leading-zeros',
              default=False,
              help='Shall we perform an extra erasure step writing zeros?')
@click.option('--stress', '-ss',
              type=click.IntRange(min=0),
              default=0,
              help='Run stress test for the given MINUTES (0 to disable)')
@click.option('--install', '-i',
              help='The name of the FSA OS to install, without the ".fsa" extension. '
                   'The file has to be in /media/workbench-images')
@click.option('--server', '-sr',
              help='Connect to a WorkbenchServer at the specified URI. '
                   'This will activate USBSneaky module, load the '
                   'settings from the server, and keep indefinitely waiting for an USB to'
                   'be plugged-in.')
@click.option('--sync-time/--no-sync-time',
              default=False,
              help='Sync the time with the Internet before executing the Workbench. '
                   'Print a warning if it cannot sync (ex. no Internet).')
@click.option('--json', '-j',
              type=cli.Path(dir_okay=False, writable=True, resolve_path=True),
              help='Write the resulting report to a JSON file.')
@click.option('--submit',
              type=cli.URL(scheme=True, username=True, password=True, host=True,
                           path=False, query_params=False, fragment=False),
              help='If set, submits the resulting Snapshot to a passed-in Devicehub.'
                   'Provide a valid URL with scheme, username, password and host.')
def erwb(**kwargs):
    click.clear()
    _sync_time = kwargs.pop('sync_time')
    _submit = kwargs.pop('submit')
    workbench = Workbench(**kwargs)
    if _sync_time:
        sync_time()
    snapshot = workbench.run()
    print('\a')  # Bip!
    if kwargs.get('server', None):
        print('You can still link the computer.')
        print('Stop the machine by pressing the power button.')
        # We wait indefinitely until the user presses CTRL-C
        # or our child process dies for some reason
        # Note that the child is a daemon so it will be terminated
        # once this main process terminates too
        workbench.usb_sneaky.join()
    if _submit:
        submit(_submit, snapshot)


def sync_time():
    """Syncs the time of the machine with the Internet."""
    # from https://stackoverflow.com/a/18720876
    try:
        client = ntplib.NTPClient()
        response = client.request('pool.ntp.org')
        subprocess.run(('date', time.strftime('%m%d%H%M%Y.%S', time.localtime(response.tx_time))),
                       stdout=subprocess.DEVNULL,
                       check=True)
        print('{}Local time set as {:%H:%M:%S}.{}'.format(Style.DIM, datetime.now(timezone.utc),
                                                          Style.NORMAL))
    except Exception:
        print('{}Time not synced with the Internet.{}'.format(Style.DIM, Style.NORMAL))


def _submit(url: urlutils.URL, snapshot: Snapshot):
    username, password = url.username, url.password
    url.username = ''  # sets password too
    session = Session(base_url=url.to_text())
    r = session.post('users/login', json={'email': username, 'password': password})
    t = r.json()['token']
    r = session.post('snapshots/',
                     data=snapshot.to_json(),
                     headers={
                         'Authorization': 'Basic {}'.format(t),
                         'Content-Type': 'application/json'
                     })
    return r.json()


def submit(url: urlutils.URL, snapshot: Snapshot):
    try:
        snapshot_server = _submit(url, snapshot)
    except (requests.ConnectionError, requests.Timeout):
        print('{}No Internet.{}'.format(Fore.YELLOW, Style.RESET_ALL),
              'Connect the computer to the Internet with an Ethernet cable to upload the report.',
              'Trying again in 10 seconds...')
        time.sleep(10)
        submit(url, snapshot)
    except requests.HTTPError as e:
        print('{}We could not auto-upload the device.{}'.format(Fore.RED, Style.RESET_ALL))
        print('This can happen for some devices, like custom-built ones,',
              'that do not have or do not report a valid S/N.')
        print('We can process them when this software is being deployed'
              'with an eReuse.org Server, like the Devicetag.io Box, but not in the actual mode.')
        print('Contact us if you have any questions.')
        print('The technical error message is as follows:')
        print(e)
    else:
        url.username = ''
        device_url = url.navigate(snapshot_server['device']['url'])
        print('{}Uploaded.{}'.format(Fore.GREEN, Style.RESET_ALL),
              'Your computer is at {}'.format(device_url.to_text()))
        print('{}Press the power button to turn this PC off.{}'.format(Style.DIM, Style.NORMAL))


if __name__ == '__main__':
    erwb()
