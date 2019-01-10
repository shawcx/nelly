#
# (c) 2008-2016 Matthew Oertle
#

import nelly


class Types:
    # Statements
    TERMINAL      = 0
    NONTERMINAL   = 1
    VARTERMINAL   = 2
    BACKREFERENCE = 3
    ANONYMOUS     = 4
    REFERENCE     = 5
    FUNCTION      = 6

    # Operations
    SLICE  = 0
    RANGE  = 1
    MEMBER = 2
    WEIGHT = 3


class Nonterminal:
    def __init__(self, _type, name=''):
        self.type        = _type
        self.name        = name
        self.options     = []
        self.decorators  = []
        self.expressions = []
        self.weight      = None


class Expression:
    def __init__(self, location):
        self.location   = location
        self.code       = None
        self.statements = []
        self.weight     = None

    def Statement(self, *args):
        self.statements.append(Statement(*args))

    def Operation(self, *args):
        self.statements[-1].operations.append(args)

    def Weight(self, weight):
        self.weight = weight


class Statement:
    def __init__(self, _type, name, *args):
        self.type       = _type
        self.name       = name
        self.args       = args
        self.operations = []

