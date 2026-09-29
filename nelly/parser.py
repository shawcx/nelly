#
# (c) 2008-2020 Matthew Shaw
#

import sys
import os
import re
import logging

import nelly

from .scanner import Scanner, Tokens
from .program import Program
from .types   import *


class Parser(object):
    def __init__(self, include_dirs=[]):
        self.include_dirs = include_dirs + [ os.path.join(nelly.root, 'grammars') ]
        self.pwd = []

        # setup the scanner based on the regular expressions
        self.scanner = Scanner(os.path.join(nelly.root, 'rules.lex'))

        # container for the compiled program
        self.program = Program()

        self.tokens_stack = []

        self.groups_stack = []
        self.group_stack  = []
        self.groups = None
        self.group  = None

    def Parse(self, grammarFile):
        grammar = grammarFile.read()

        self.pwd.append(os.path.dirname(grammarFile.name))

        logging.debug('Parsing %s (%d bytes)', grammarFile.name, len(grammar))

        # drop /* */ comments so they can appear anywhere
        comments = ('start_comment', 'comment', 'end_comment')
        self.tokens = Tokens(t for t in self.scanner.Scan(grammar) if t[0] not in comments)

        # keep a reference to the tokens for when included files are parsed
        self.tokens_stack.append(self.tokens)

        # iterate over all the tokens
        while self.tokens:
            (token,value,line,col) = self.tokens.Next()

            # handle all the top-level tokens
            if 'nonterminal' == token:
                if value.startswith('::'):
                    value = value[2:]
                self._nonterminal(Types.NONTERMINAL, value)
            elif 'varterminal' == token:
                if value.startswith('::'):
                    value = value[2:]
                self._nonterminal(Types.VARTERMINAL, value)
            elif 'include' == token:
                self._include()
            elif 'start_python_code' == token:
                if r'<%pre' == value:
                    self.program.preamble.append(self._python_code('pre'))
                elif r'<%post' == value:
                    self.program.postscript.append(self._python_code('post'))
                else:
                    raise nelly.error('Please specify pre or post in code section')
            else:
                raise nelly.error('Unhandled %s %s at %d:%d', token, repr(value), line, col)

        self.tokens_stack.pop()
        return self.program

    def _nonterminal(self, _type, name):
        # create a new container and add it to the program
        nonterminal = Nonterminal(_type, name)
        self.program.nonterminals[name] = nonterminal

        (token,value,line,col) = self.tokens.Next()

        # parse any optional arguments for the non-terminal
        if 'lparen' == token:
            while True:
                (token,value,line,col) = self.tokens.Next()
                if 'rparen' == token:
                    break
                elif 'comma' == token:
                    continue
                elif 'option' == token:
                    nonterminal.options.append(value)
                    if value == 'start':
                        self.program.start.append(name)
                elif 'decorator' == token:
                    nonterminal.decorators.append(value[1:])
                else:
                    raise nelly.error('Unknown option: %s %s', token, value)
            (token,value,line,col) = self.tokens.Next()

        if 'colon' != token:
            raise nelly.error('Parse error, missing colon at line %d, column %d', line, col)

        # parse zero or more expressions until a semicolon is found
        self._expressions('pipe', 'semicolon', nonterminal)

    def _expressions(self, delimiter, sentinel, nonterminal, owner=None):
        # groups and function arguments are anonymous, so report errors
        # against the enclosing named non-terminal
        owner = owner or nonterminal.name

        (token,value,line,col) = self.tokens.Peek()
        expression = Expression((line,col), owner)

        while self.tokens:
            (token,value,line,col) = self.tokens.Next()

            if sentinel == token:
                nonterminal.expressions.append(expression)
                break
            elif delimiter == token:
                nonterminal.expressions.append(expression)
                expression = Expression((line,col), owner)
            elif 'lparen' == token:
                anonterminal = Nonterminal(Types.ANONYMOUS)
                expression.Statement(Types.ANONYMOUS, anonterminal)
                self._expressions('pipe', 'rparen', anonterminal, owner)
            elif token in ['start_single_quote', 'start_double_quote', 'start_triple_quote']:
                quote = self._quote()
                expression.Statement(Types.TERMINAL, quote)
            elif token in ['start_single_bytes', 'start_double_bytes', 'start_triple_bytes']:
                byte_quote = self._quote()
                expression.Statement(Types.TERMINAL, byte_quote)
            elif 'nonterminal' == token:
                expression.Statement(Types.NONTERMINAL, value)
            elif 'varterminal' == token:
                expression.Statement(Types.VARTERMINAL, value)
            elif 'backref' == token:
                expression.Statement(Types.BACKREFERENCE, value)
            elif 'function' == token:
                functerminal = Nonterminal(Types.ANONYMOUS)
                self._expressions('comma', 'rparen', functerminal, owner)
                expression.Statement(Types.FUNCTION, value[1:], functerminal)
            elif 'reference' == token:
                expression.Statement(Types.REFERENCE, value[1:])
            elif 'constant' == token:
                expression.Statement(Types.TERMINAL, value)
            elif 'start_python_code' == token:
                expression.code = self._python_code(nonterminal.name)
            elif 'lbracket' == token:
                try:
                    expression.Operation(Types.SLICE, self._slice())
                except IndexError:
                    raise nelly.error('Applying slice to nothing at line %d, column %d', line, col)
            elif 'lcurley' == token:
                try:
                    expression.Operation(Types.RANGE, self._range())
                except IndexError:
                    raise nelly.error('Applying range to nothing at line %d, column %d', line, col)
            elif 'langle' == token:
                expression.Weight(self._weight())
            elif 'empty' == token:
                pass
            elif 'semicolon' == token:
                raise nelly.error('Missing ")" before ";" at line %d, column %d', line, col)
            else:
                raise nelly.error('Unhandled token "%s" at line %d, column %d', token, line, col)
        else:
            closing = {'semicolon': ';', 'rparen': ')'}[sentinel]
            raise nelly.error('Missing "%s" for the expression starting at line %d, column %d', closing, *expression.location)

    def _quote(self):
        # this will always be the quoted value
        (token,value,line,col) = self.tokens.Next()
        # this will always be the terminal quote
        self.tokens.Next()
        return value

    #
    # Slice a string
    #
    def _slice(self):
        front = None
        back  = None
        start = False

        (token,value,line,col) = self.tokens.Next()
        if 'constant' == token:
            front = value
            start = True
            (token,value,line,col) = self.tokens.Next()

        if 'rbracket' == token:
            if False == start:
                raise nelly.error('Empty slice at line %d, column %d', line, col)
            return (front,front+1)

        elif 'colon' != token:
            raise nelly.error('Missing colon at line %d, column %d', line, col)

        (token,value,line,col) = self.tokens.Next()
        if 'constant' == token:
            back = value
            (token,value,line,col) = self.tokens.Next()
        elif 'rbracket' != token:
            raise nelly.error('Missing ] at line %d, column %d', line, col)

        return (front,back)

    #
    # Repeat a range
    #
    def _range(self):
        lower = 0
        upper = 0

        (token,value,line,col) = self.tokens.Next()
        if 'constant' != token:
            raise nelly.error('Missing range at line %d, column %d', line, col)

        lower = value
        upper = value

        (token,value,line,col) = self.tokens.Next()
        if 'rcurley' == token:
            return (lower,upper)
        elif 'comma' != token:
            raise nelly.error('Missing comma at line %d, column %d', line, col)

        (token,value,line,col) = self.tokens.Next()
        if 'constant' == token:
            upper = value
        else:
            raise nelly.error('Missing range at line %d, column %d', line, col)

        (token,value,line,col) = self.tokens.Next()
        if 'rcurley' != token:
            raise nelly.error('Missing } at line %d, column %d', line, col)

        if lower > upper:
            lower,upper = upper,lower

        return (lower,upper)

    def _weight(self):
        (token,value,line,col) = self.tokens.Next()
        if 'constant' != token:
            raise nelly.error('Missing weight at line %d, column %d', line, col)
        (token,ignore,line,col) = self.tokens.Next()
        if 'rangle' != token:
            raise nelly.error('Missing > at %d, column %d', line, col)
        return value

    #
    # Compile the Python into a code object
    #
    def _python_code(self, name):
        (token,value,line,col) = self.tokens.Next()

        values = [s for s in value.split('\n') if s.strip()] or ['']

        # save the whitepsace of the first line
        ws = re.compile(r'\s*').match(values[0]).group()

        # check indentation
        if [s for s in values if not s.startswith(ws)]:
            raise nelly.error('Bad indentation in code block at line %d, column %d', line, col)

        # strip and rejoin the code
        codeblock = '\n'.join(s[len(ws):] for s in values)

        # eat the end_python_code token
        self.tokens.Next()

        try:
            return compile(codeblock, '<'+name+'>', 'exec')
        except SyntaxError as e:
            raise nelly.error('%d: %s: %s', e.lineno, e.msg, repr(e.text))

    #
    # Include other BNF files
    #
    def _include(self):
        (token,value,line,col) = self.tokens.Next()

        # file names are quoted
        if token not in ['start_single_quote', 'start_double_quote', 'start_triple_quote']:
            raise nelly.error('quoted file path expected')

        # get the quoted value
        path = self._quote()

        # use the first include directory that has the file
        for include_dir in self.pwd[-1:] + self.include_dirs:
            fullpath = os.path.join(include_dir, path)
            if os.path.isfile(fullpath):
                break
        else:
            raise nelly.error('Could not find include file %s', repr(path))

        logging.debug('Including file %s', repr(fullpath))

        # compile it inline
        try:
            with open(fullpath, 'r') as content:
                self.Parse(content)
        except OSError as e:
            raise nelly.error('Could not read include file %s: %s', repr(fullpath), e.strerror) from None
        self.pwd.pop()

        # restore the current tokens
        self.tokens = self.tokens_stack[-1]
