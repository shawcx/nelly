#
# (c) 2020 Matthew Shaw
#

import sys
import os
import logging

import nelly


class Dictionary:
    def __init__(self, output):
        self.output = output

    def Walk(self, program):
        strings = set()
        for name,nonterminal in program.nonterminals.items():
            for expression in nonterminal.expressions:
                for statement in expression.statements:
                    if statement.type != 0:
                        continue
                    strings.add(statement.value)

        strings = list(strings)
        strings.sort()

        logging.info('Writing dictionary: %s', self.output)
        with open(self.output, 'w') as fp:
            for string in strings:
                if string == '\x00':
                    continue
                fp.write(string)
                fp.write('\n')
