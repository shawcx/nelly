#
# (c) 2008-2016 Matthew Oertle
#

import marshal

try:
    import cPickle as pickle
except ImportError:
    import pickle


class Program(object):
    def __init__(self):
        self.nonterminals = {}
        self.preamble     = []
        self.postscript   = []

        self.start = []

    def Save(self):
        return pickle.dumps(
            dict(
                nonterminals = self.nonterminals,
                preamble     = self.preamble,
                postscript   = self.postscript,
                )
            )

    @classmethod
    def Load(cls, package):
        mapping = pickle.loads(package)

        program = Program()
        program.preamble     = [marshal.loads(m) for m in mapping['preamble']]
        program.postscript   = [marshal.loads(m) for m in mapping['postscript']]

        program.nonterminals = mapping['nonterminals']
        for name,nonterminal in program.nonterminals.items():
            if 'start' in nonterminal.options:
                program.start.append(name)
            for expression in nonterminal.expressions:
                if not expression.code:
                    continue
                expression.code = marshal.loads(expression.code)

        return program
