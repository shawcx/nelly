#!/usr/bin/env python3

import sys

import nelly.main

if '__main__' == __name__:
    try:
        sys.exit(nelly.main.main())
    except nelly.error as e:
        print(e)
        sys.exit(-1)
