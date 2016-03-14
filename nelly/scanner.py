#
# (c) 2008-2016 Matthew Oertle
#

import re
import collections
import logging

from .types import Tokens

_functions = {}


def action(fn):
    if hasattr(fn, 'func_name'):
        _functions[fn.func_name] = None
    else:
        _functions[fn.__name__] = None
    return fn


class Scanner(object):
    def __init__(self, path):
        for fn in _functions:
            _functions[fn] = getattr(self, fn)

        rules = open(path, 'rb').read()
        rules = eval(rules, _functions)

        self.states = collections.defaultdict(list)

        states = rules.get('states', {})
        for state,patterns in states.items():
            for pattern in patterns:
                self.states[state].append((re.compile(pattern[0]),pattern[1],(pattern[2:])))

    def Scan(self, stream):
        self.tokens  = Tokens()
        self.stack   = ['bnf']
        self.current = []

        self.linenumber = 1
        self.column     = 1

        while stream:
            match = None
            # use the patterns from the state at the back of the stack
            for pattern,fn,args in self.states[self.stack[-1]]:
                match = pattern.match(stream)
                if match:
                    break

            stream = stream[match.end():]

            args = (match.group(),) + args
            try:
                fn(*args)
            except SyntaxError as e:
                raise SyntaxError('"%s" at %d, Column %d', e, self.linenumber, self.column)

            group = match.group()
            if '\n' in group:
                self.linenumber += group.count('\n')
                self.column = 1 + len(group[group.rindex('\n')+1:])
            else:
                self.column += len(group)

        if self.current:
            self.AddToken(''.join(self.current), self.stack[-1])

        return self.tokens

    @action
    def Push(self, match, mode):
        self.stack.append(mode)

        match = match.strip()

        self.AddToken(match, 'start_' + mode)

        self.current = []

    @action
    def Pop(self, match):
        match = match.strip()
        mode  = self.stack.pop()

        self.AddToken(''.join(self.current), mode)
        self.current = []

        self.AddToken(match, 'end_' + mode)

    @action
    def AddToken(self, match, name):
        self.tokens.Add(name, match, self.linenumber, self.column)

    @action
    def Append(self, match):
        self.current.append(match)

    @action
    def AddNumber(self, match):
        self.tokens.Add('constant', eval(match), self.linenumber, self.column)

    @action
    def Sub(self, match):
        self.current += '_g_var["' + match + '"]'

    @action
    def Unescape(self, match):
        try:
            self.current += match.decode('string_escape')
        except AttributeError: # python3 support
            self.current += bytes(match, 'utf-8').decode('unicode_escape')

    @action
    def Ignore(self, match):
        pass

    @action
    def Error(self, match):
        raise SyntaxError(match)
