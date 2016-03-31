#!/usr/bin/env python

import sys
import os

from distutils.core import setup

setup(
    name = 'nelly',
    version = '0.4',
    author = 'Matthew Oertle',
    author_email = 'moertle@gmail.com',
    description = 'A grammar-based generator',
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
)
