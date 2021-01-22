#
# (c) 2020 Matthew Shaw
#

import sys
import os
import logging

import nelly

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
            for expression in nonterminal.expressions:
                for statement in expression.statements:
                    if statement.type != 0:
                        continue
                    strings.add(statement.value)

        strings = list(strings)
        strings.sort()

        logging.info('Writing dictionary: %s', self.output)

        with open(self.output, 'w') as fp:
            idx = 0
            for string in strings:
                escaped = []
                for s in string:
                    if not 0x1f < ord(s) < 0x7f:
                        s = '\\x%.2X' % ord(s)
                    elif s == '"':
                        s = '\\"'
                    elif s == '\\':
                        s = '\\\\'
                    escaped.append(s)
                string = ''.join(escaped)
                idx += 1
                fp.write('%s_%d="%s"\n' % (self.name, idx, string))
