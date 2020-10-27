#
# (c) 2008-2020 Matthew Shaw
#

import marshal

import pickle


class Program(object):
    def __init__(self):
        self.nonterminals = {}
        self.preamble     = []
        self.postscript   = []
        self.start        = []

    def Save(self):
        for name,nonterminal in self.nonterminals.items():
            for expression in nonterminal.expressions:
                if not expression.code:
                    continue
                expression.code = marshal.dumps(expression.code)

        return pickle.dumps(
            dict(
                nonterminals = self.nonterminals,
                preamble     = [marshal.dumps(m) for m in self.preamble],
                postscript   = [marshal.dumps(m) for m in self.postscript],
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
