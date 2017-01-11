import re

from setuptools import setup, find_packages


# Dynamically calculate the version
version = __import__('erwb').get_version()

# Collect installation requirements
def read_requirements(path):
    with open(path) as reqf:
        dep_re = re.compile(r'^([^\s#]+)')
        return [m.group(0) for m in
                (dep_re.match(l) for l in reqf)
                if m]

inst_reqs = read_requirements('requirements.txt')
full_reqs = read_requirements('requirements-full.txt')

setup(
    name="ereuse-workbench",
    version=version,
    packages=find_packages(),
    license='AGPLv3 License',
    description=('The eReuse Workbench (formerly Device Inventory) is '
                 'a tool to help with the diagnostic and inventory of computers. '
                 'It retrieves details of the hardware and, optionally, '
                 'runs some health and benchmark tests.'),
    scripts=['scripts/erwb'],
    package_data={'erwb': [
        'config.ini',
        'config_logging.json',
        'data/*'
    ]},
    url='https://github.com/eReuse/workbench',
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
    extras_require={'full': full_reqs},
)
