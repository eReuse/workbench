from setuptools import find_packages, setup

with open('README.md') as f:
    long_description = f.read()

test_requires = [
    'pytest',
    'requests_mock'
]

setup(
    name='ereuse-workbench',
    version='11.0b3',
    url='https://github.com/eReuse/workbench',
    license='Affero',
    packages=find_packages(),
    description='Hardware report of the computer including components,'
                ' testing, benchmarking, erasing, and installing an OS.',
    author='eReuse.org team',
    author_email='x.bustamante@ereuse.org',
    python_requires='>=3.5.3',
    long_description=long_description,
    long_description_content_type='text/markdown',
    install_requires=[
        'python-dateutil',
        'pydash',
        'tqdm',
        'pySMART.smartx',
        'pyudev',
        'requests',
        'ereuse-utils[usb_flash_drive,session,cli]>=0.4.0b18',
        'colorama',
        'click >= 6.0',
        'click-spinner',
        'inflection',
        'ntplib'
    ],
    setup_requires=[
        'pytest-runner'
    ],
    extras_require={
        'test': test_requires,
    },
    tests_require=test_requires,
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
    ],
    py_modules=['ereuse_workbench'],
    entry_points={
        'console_scripts': [
            'erwb = ereuse_workbench.erwb:erwb',
        ],
    },
)
