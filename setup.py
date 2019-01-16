#!/usr/bin/env python3

import sys
import os

from setuptools import setup

exec(compile(open('nelly/version.py').read(),'version.py','exec'))

def findDataFiles(root):
    paths = []
    trim = len(root) + 1
    for base,directories,filenames in os.walk(root):
        if base.endswith('__pycache__'):
            continue
        for filename in filenames:
            if filename.endswith('.py'):
                continue
            paths.append(os.path.join(base, filename)[trim:])
    return paths

setup(
    name             = 'nelly',
    author           = __author__,
    author_email     = __email__,
    version          = __version__,
    license          = __license__,
    description      = 'Python Test Case Generator',
    long_description = open('docs/README.rst').read(),
    url              = 'https://github.com/moertle/nelly',
    entry_points = {
        'console_scripts' : [
            'nelly = nelly.main:entry',
            ]
        },
    packages = [
        'nelly',
        ],
    package_data = {
        'nelly': findDataFiles('nelly')
        },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Topic :: Software Development :: Testing',
        'Programming Language :: Python :: 3',
        ]
    )
