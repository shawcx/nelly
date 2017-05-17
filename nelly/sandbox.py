#
# (c) 2008-2016 Matthew Oertle
#

from __future__ import print_function

import sys
import os
import random
import logging

import nelly

from .types import *


class Sandbox:
    def __init__(self, variables):
        self.lookup = dict(enumerate((
            self.Terminal,
            self.Nonterminal,
            self.Varterminal,
            self.Backreference,
            self.Anonymous,
            self.Reference,
            self.Function,
            )))

        self.globals = {}
        self.globals['_g_var'] = {
            '$NT' : self.Nonterminal,
            '$VT' : self.Varterminal,
            '$BR' : self.Backreference,
            }
        self.globals['_g_var'].update(variables)

        self.backref = {}
        self.record  = []

    def choose(self, items, noweight=False):
        if not noweight:
            r = random.random()
            choice = 0
            for i in items:
                print(r, i.weight)
                if r < i.weight:
                    break
                r -= i.weight
                choice += 1
            print()
            self.record.append(choice)
        else:
            choice = random.randrange(len(items))
            self.record.append(choice)
        return items[choice]

    def Execute(self, program):
        self.program = program

        for pycode in self.program.preamble:
            ok = self.__ExecPython(pycode)
            if ok == False:
                logging.error('Terminating on preamble')
                return

        try:
            name = self.choose(self.program.start, True)
        except ValueError:
            raise nelly.error('No entry points')

        self.Nonterminal(name)

        for pycode in self.program.postscript:
            ok = self.__ExecPython(pycode)
            if ok == False:
                logging.error('Terminating on postscript')
                return

    def Expression(self, expression):
        retval = ''
        for statement in expression.statements:
            function = self.lookup[statement.type]

            if not statement.operations:
                current = function(statement.name, *statement.args)
            else:
                current = None

                for operation in statement.operations:
                    if operation[0] == Types.SLICE:
                        if current is None:
                            current = function(statement.name, *statement.args)
                        current = current[slice(*operation[1])]
                    elif operation[0] == Types.RANGE:
                        count = random.randint(*operation[1])
                        if current is None:
                            if count == 0:
                                current = ''
                            else:
                                current = function(statement.name, *statement.args)
                                for idx in range(count - 1):
                                    current += function(statement.name, *statement.args)
                        else:
                            current = current * count

            if isinstance(current, str):
                retval += current
            else:
                if retval:
                    logging.debug('Stomping previous data')
                retval = current

        self.globals['_g_var']['$*'] = None
        self.globals['_g_var']['$$'] = retval

        if expression.code:
            self.__ExecPython(expression.code)

        return retval

    def Nonterminal(self, name):
        try:
            nonterminal = self.program.nonterminals[name]
        except KeyError as e:
            raise nelly.error('Unknown nonterminal: "%s"', name)

        retval = self.Expression(self.choose(nonterminal.expressions))
        self.backref[name] = retval
        return retval

    def Varterminal(self, name):
        try:
            varterminal = self.program.nonterminals[name]
        except KeyError as e:
            raise nelly.error('Unknown varterminal: "%s"', name)

        self.Expression(self.choose(varterminal.expressions))
        self.backref[name] = self.globals['_g_var']['$*']
        return self.globals['_g_var']['$*']

    def Terminal(self, value):
        return value

    def Backreference(self, name):
        return self.backref.get(name[1:], None)

    def Anonymous(self, anonterminal):
        retval = self.Expression(self.choose(anonterminal.expressions))
        return retval

    def Function(self, function, arguments):
        fn = eval(function[:-1], self.globals)
        args = []
        for expression in arguments.expressions:
            args.append(self.Expression(expression))
        retval = fn(*args)
        return retval

    def Reference(self, name):
        return eval(name, self.globals)

    def __ExecPython(self, pycode):
        try:
            exec(pycode, self.globals)
        except KeyError as e:
            name, = e.args
            if name[0] == '$':
                raise nelly.error('Undeclared variable "%s"', name[1:])
            raise
        except SystemExit:
            return False
