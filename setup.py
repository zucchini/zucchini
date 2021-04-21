#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

import sys
from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [
    'click==6.7',
    'gitdb2==2.0.3',
    'GitPython==2.1.8',
    'PyYAML==5.1',
    'smmap2==2.0.3',
    'requests==2.20.0',
    'boto3==1.5.19',
    'subprocess32==3.2.7;python_version<"3.0"',
    'arrow==0.12.1',
]

setup_requirements = [
    # TODO(zucchini): put setup requirements (distutils extensions, etc.) here
]

test_requirements = [
    # TODO: put package test requirements here
]

setup(
    name='zucchini',
    version='2.0.6',
    description="Zucchini is an automatic grader tool for use in grading programming assignments.",
    long_description=readme + '\n\n' + history,
    author="Zucchini Team",
    author_email='team@zucc.io',
    url='https://github.com/zucchini/zucchini',
    packages=find_packages(include=['zucchini', 'zucchini.*']),
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
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    test_suite='tests',
    tests_require=test_requirements,
    setup_requires=setup_requirements,
)
