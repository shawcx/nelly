#
# (c) 2008-2016 Matthew Oertle
#

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
            '$_Nonterminal'   : self.Nonterminal,
            '$_Varterminal'   : self.Varterminal,
            '$_Backreference' : self.Backreference,
            }
        self.globals['_g_var'].update(variables)

        self.backreference = {}
        self.record = []

    def choose(self, items, pick=None):
        if None is pick:
            choice = random.randrange(len(items))
            self.record.append(choice)
            return items[choice]
        else:
            return items[pick]

    def Execute(self, program):
        self.program = program

        for pycode in self.program.preamble:
            self.__ExecPython(pycode)

        try:
            entry_point = self.choose(self.program.start)
        except ValueError:
            raise nelly.error('No entry points')

        #logging.debug('Entry point: "%s"', entry_point)

        self.Nonterminal(entry_point)

        for pycode in self.program.postscript:
            self.__ExecPython(pycode)

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

                    elif operation[0] == Types.WEIGHT:
                        pass

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

        expression = self.choose(nonterminal.expressions)

        retval = self.Expression(expression)
        self.backreference[name] = retval
        return retval

    def Varterminal(self, name):
        try:
            varterminal = self.program.nonterminals[name]
        except KeyError as e:
            raise nelly.error('Unknown varterminal: "%s"', name)

        expression = self.choose(varterminal.expressions)

        self.Expression(expression)

        self.backreference[name] = self.globals['_g_var']['$*']

        return self.globals['_g_var']['$*']

    def Terminal(self, value):
        return value

    def Backreference(self, name):
        return self.backreference.get(name[1:], None)

    def Anonymous(self, anonterminal):
        expression = self.choose(anonterminal.expressions)
        retval = self.Expression(expression)
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
            if e.message[0] == '$':
                raise nelly.error('Undeclared variable "%s"', e.message[1:])
            raise
        except SystemExit:
            pass
