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
    )
