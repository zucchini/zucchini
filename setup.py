#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

import sys
from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

python2_requirements = [
    'subprocess32==3.2.7'
]

requirements = [
    'click==6.7',
    'gitdb2==2.0.3',
    'GitPython==2.1.8',
    'PyYAML==3.12',
    'smmap2==2.0.3',
    'requests==2.18.4',
]

if sys.version_info[0] < 3:
    requirements += python2_requirements

setup_requirements = [
    # TODO(zucchini): put setup requirements (distutils extensions, etc.) here
]

test_requirements = [
    # TODO: put package test requirements here
]

setup(
    name='zucchini',
    version='0.1.0',
    description="Zucchini is an automatic grader tool for use in grading programming assignments.",
    long_description=readme + '\n\n' + history,
    author="Zucchini Team",
    author_email='team@zucc.io',
    url='https://github.com/zucchini/zucchini',
    packages=find_packages(include=['zucchini']),
    entry_points={
        'console_scripts': [
            'zucc=zucchini.cli:cli'
        ]
    },
    include_package_data=True,
    install_requires=requirements,
    license="Apache Software License 2.0",
    zip_safe=False,
    keywords='zucchini',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    test_suite='tests',
    tests_require=test_requirements,
    setup_requires=setup_requirements,
)
