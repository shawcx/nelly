#
# (c) 2008-2020 Matthew Shaw
#

import os

DEBUG = False
root  = os.path.dirname(__file__)

class error(Exception):
    def __init__(self, fmt, *args):
        self.str = fmt % args

    def __str__(self):
        return self.str

from . import version

from .program  import Program
from .parser   import Parser
from .sandbox  import Sandbox

from .utils import *
