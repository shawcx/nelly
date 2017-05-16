#!/usr/bin/env python

import sys
import os

from distutils.core import setup

exec(compile(open('nelly/version.py').read(),'version.py','exec'))

setup(
    name             = 'nelly',
    author           = __author__,
    author_email     = __email__,
    version          = __version__,
    license          = __license__,
    description      = 'Python Test Case Generator',
    long_description = open('README.rst').read(),
    packages = [
        'nelly',
        ],
    package_data = {
        'nelly': [
            'rules.lex',
            'bnf/constants.bnf'
            ]
        },
    scripts = [
        'bin/nelly',
        ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Topic :: Software Development :: Testing',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        ]
    )
