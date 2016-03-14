#
# (c) 2008-2016 Matthew Oertle
#

class Types(object):
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

class Nonterminal(object):
    def __init__(self, _type, name=''):
        self.type        = _type
        self.name        = name
        self.options     = []
        self.expressions = []

class Expression(object):
    def __init__(self, location):
        self.location = location
        self.code = None
        self.statements = []
        #self.operations = []

    def Statement(self, *args):
        self.statements.append(Statement(*args))

    def Operation(self, *args):
        self.statements[-1].operations.append(args)

class Statement(object):
    def __init__(self, _type, name, *args):
        self.type = _type
        self.name = name
        self.args = args
        self.operations = []

class Tokens(list):
    def __init__(self, *args):
        super(Tokens, self).__init__(*args)
        self.locations = []

    def Add(self, token, value, line, col):
        list.append(self, (token, value, line, col))

    def Next(self):
        try:
            return self.pop(0)
        except IndexError:
            raise SyntaxError('No more tokens')

    def Peek(self):
        try:
            return self.__getitem__(0)
        except IndexError:
            raise SyntaxError('No more tokens')
