from pathlib import Path

from setuptools import find_packages, setup

test_requires = [
    'pytest',
    'requests_mock'
]

setup(
    name='ereuse-workbench',
    version='11.0b9',
    url='https://github.com/ereuse/workbench',
    license='Affero',
    packages=find_packages(),
    description='Hardware report of the computer including components,'
                ' testing, benchmarking, erasing, and installing an OS.',
    author='eReuse.org team',
    author_email='x.bustamante@ereuse.org',
    python_requires='>=3.5.3',
    long_description=Path('README.md').read_text(),
    long_description_content_type='text/markdown',
    install_requires=[
        'colorama',
        'click >= 7.0',
        'ereuse-utils[cli,getter,session,usb_flash_drive]>=0.4.0b49',
        'inflection',
        'ntplib',
        'python-dateutil',
        'pySMART.smartx',
        'requests'
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
