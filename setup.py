from setuptools import setup, find_packages


# Dynamically calculate the version
version = __import__('device_inventory').get_version()

# Collect installation requirements
with open('requirements.txt') as reqf:
    import re
    dep_re = re.compile(r'^([^\s#]+)')
    inst_reqs = [m.group(0) for m in
                 [dep_re.match(l) for l in reqf]
                 if m]

setup(
    name="device-inventory",
    version=version,
    packages=find_packages(),
    license='AGPLv3 License',
    description=('The Device Inventory is a tool to help the inventory '
                 'of computers. It retrieves details of the hardware '
                 'information and, optionally, runs some health and '
                 'benchmark tests.'),
    scripts=['scripts/device-inventory', 'scripts/di-stress-test'],
    package_data={'device_inventory': [
        'config.ini',
        'config_logging.json',
        'data/*'
    ]},
    url='https://github.com/eReuse/device-inventory',
    author='eReuse team',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: GNU Affero General Public License v3',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Topic :: System :: Logging',
        'Topic :: Utilities',
    ],
    install_requires=inst_reqs,
)
