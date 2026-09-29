#
# (c) 2020 Matthew Shaw
#

import sys
import os
import logging

import nelly

from .types import *

# convert punctuation to underscore
p = '!"#$%&\'()*+,-./:;<=>?@[\\]^`{|}~'
remove = str.maketrans(p, '_' * len(p))


class Dictionary:
    def __init__(self, output):
        self.output = output
        prefix = os.path.basename(output)
        self.name = prefix.translate(remove)

    def Walk(self, program):
        strings = set()
        for name,nonterminal in program.nonterminals.items():
            self._collect(nonterminal, strings)

        strings = sorted(strings)

        logging.info('Writing dictionary: %s', self.output)

        with open(self.output, 'w') as fp:
            idx = 0
            for string in strings:
                escaped = []
                for c in string:
                    if not 0x1f < c < 0x7f:
                        s = '\\x%.2X' % c
                    elif c == ord('"'):
                        s = '\\"'
                    elif c == ord('\\'):
                        s = '\\\\'
                    else:
                        s = chr(c)
                    escaped.append(s)
                string = ''.join(escaped)
                idx += 1
                fp.write('%s_%d="%s"\n' % (self.name, idx, string))

    def _collect(self, nonterminal, strings):
        # recurse into groups and function arguments, which are anonymous
        # nonterminals that do not appear in program.nonterminals
        for expression in nonterminal.expressions:
            for statement in expression.statements:
                if statement.type == Types.ANONYMOUS:
                    self._collect(statement.value, strings)
                elif statement.type == Types.FUNCTION:
                    self._collect(statement.args[0], strings)
                elif statement.type == Types.TERMINAL:
                    value = statement.value
                    # numeric constants are function arguments, not output
                    if isinstance(value, str):
                        value = value.encode(nelly.encode or 'utf-8')
                    elif not isinstance(value, bytes):
                        continue
                    if value:
                        strings.add(value)
