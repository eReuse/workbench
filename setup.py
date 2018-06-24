from setuptools import find_packages, setup

with open('README.md') as f:
    long_description = f.read()

setup(
    name='ereuse-workbench',
    version='10.0b6',
    packages=find_packages(),
    license='AGPLv3 License',
    description='The eReuse Workbench is '
                'a toolset to help with the diagnostic, benchmarking, '
                'inventory and installation of computers, '
                'with the optional assistance of a local server.',
    scripts=['scripts/erwb'],
    url='https://github.com/eReuse/workbench',
    author='eReuse.org team',
    author_email='x.bustamante@ereuse.org',
    long_description=long_description,
    long_description_content_type='text/markdown',
    install_requires=[
        'python-dateutil',
        'pydash',
        'tqdm',
        'pySMART.smartx',
        'pyudev',
        'requests',
        'ereuse-utils [usb_flash_drive]',
        'colorama',
        'requests-toolbelt'
    ],
    setup_requires=[
        'pytest-runner'
    ],
    tests_require=[
        'pytest',
        'pytest-mock'
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: GNU Affero General Public License v3',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.5',
        'Topic :: System :: Logging',
        'Topic :: Utilities',
    ]
)
