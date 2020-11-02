#
# (c) 2008-2020 Matthew Shaw
#

import binascii
import codecs
import collections
import re

import nelly

_functions = {}


def action(fn):
    if hasattr(fn, 'func_name'):
        _functions[fn.func_name] = None
    else:
        _functions[fn.__name__] = None
    return fn


class Tokens(list):
    def __init__(self, *args):
        super(Tokens, self).__init__(*args)
        self.locations = []

    def Add(self, token, value, line, col):
        super(Tokens, self).append((token, value, line, col))

    def Next(self):
        try:
            return self.pop(0)
        except IndexError:
            raise nelly.error('No more tokens')

    def Peek(self):
        try:
            return self.__getitem__(0)
        except IndexError:
            raise nelly.error('No more tokens')


class Scanner:
    def __init__(self, path):
        for fn in _functions:
            _functions[fn] = getattr(self, fn)

        rules = open(path, 'r').read()
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
                raise nelly.error('Syntax error: "%s" at %d, Column %d', e, self.linenumber, self.column) from None

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
    def AddChar(self, match):
        if match.startswith(r'\x'):
            match = int(match[2:], 16)
        elif match.startswith(r'\d'):
            match = int(match[2:])
        else:
            raise SyntaxError(match)
        self.AddToken(chr(match), 'constant')

    @action
    def AddNumber(self, match):
        self.AddToken(eval(match), 'constant')

    @action
    def Sub(self, match):
        self.current.append('_g_var["' + match + '"]')

    @action
    def Unescape(self, match):
        try:
            self.current.append(codecs.unicode_escape_decode(match)[0])
        except UnicodeDecodeError:
            raise SyntaxError(match)

    @action
    def AppendByte(self, match):
        try:
            self.current.append(bytes([ord(match)]))
        except ValueError:
            raise SyntaxError('non-ASCII character in byte string: ' + match)

    @action
    def UnescapeHexByte(self, match):
        self.current.append(binascii.unhexlify(match[2:]))

    @action
    def UnescapeByte(self, match):
        lookup = {
            "\\" : b'\\',
            "'"  : b"'",
            '"'  : b'"',
            'a'  : b'\a',
            'b'  : b'\b',
            'f'  : b'\f',
            'n'  : b'\n',
            'r'  : b'\r',
            't'  : b'\t',
            'v'  : b'\v',
            }
        self.current.append(lookup[match[1]])

    @action
    def PopByte(self, match):
        match = match.strip()
        mode  = self.stack.pop()
        self.AddToken(b''.join(self.current), mode)
        self.current = []
        self.AddToken(match, 'end_' + mode)

    @action
    def Ignore(self, match):
        pass

    @action
    def Error(self, match):
        raise SyntaxError(match)
