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
    def __init__(self, variables=None):
        self.globals = {}
        self.globals['_g_var'] = {
            '$NT' : self.Nonterminal,
            '$VT' : self.Varterminal,
            '$BR' : self.Backreference,
            }
        if variables:
            self.globals['_g_var'].update(variables)
        self.backref = {}
        self.record  = []

    def choose(self, items, noweight=False):
        if not noweight:
            r = random.random()
            choice = 0
            for i in items:
                if i.weight is None:
                    continue
                if r < i.weight:
                    break
                r -= i.weight
                choice += 1
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
                raise nelly.error('Terminating on preamble')

        try:
            name = self.choose(self.program.start, True)
        except ValueError:
            raise nelly.error('No entry points')

        if not name.startswith('$'):
            self.Nonterminal(name)
        else:
            self.Varterminal(name)

        for pycode in self.program.postscript:
            ok = self.__ExecPython(pycode)
            if ok == False:
                raise nelly.error('Terminating on postscript')

        return self.globals['_g_var'].get('$$')

    def Expression(self, expression):
        retval = ''
        for statement in expression.statements:
            statementFunction = Sandbox.LOOKUP[statement.type]
            if not statement.operations:
                current = statementFunction(self, statement.value, *statement.args)
            else:
                current = None

                for operation in statement.operations:
                    if operation[0] == Types.SLICE:
                        if current is None:
                            current = statementFunction(self, statement.value, *statement.args)
                        current = current[slice(*operation[1])]
                    elif operation[0] == Types.RANGE:
                        count = random.randint(*operation[1])
                        if current is None:
                            if count == 0:
                                current = ''
                            else:
                                current = statementFunction(self, statement.value, *statement.args)
                                for idx in range(count - 1):
                                    current += statementFunction(self, statement.value, *statement.args)
                        else:
                            current = current * count

            if isinstance(current, str):
                retval += current
            else:
                if isinstance(current, retval.__class__):
                    retval += current
                else:
                    if retval:
                        logging.warn('Stomping previous data')
                    retval = current

        self.globals['_g_var']['$*'] = None
        self.globals['_g_var']['$$'] = retval

        if expression.code:
            ok = self.__ExecPython(expression.code)
            if ok == False:
                logging.error('Terminating on semantic action')
                raise SystemExit

        return retval

    def Nonterminal(self, name):
        try:
            nonterminal = self.program.nonterminals[name]
        except KeyError as e:
            raise nelly.error('Unknown nonterminal: "%s"', name) from None

        retval = self.Expression(self.choose(nonterminal.expressions))
        for decorator in nonterminal.decorators:
            retval = self.__decorator(decorator)(retval)

        self.globals['_g_var']['$$'] = retval
        self.backref[name] = retval
        return retval

    def Varterminal(self, name):
        try:
            varterminal = self.program.nonterminals[name]
        except KeyError as e:
            raise nelly.error('Unknown varterminal: "%s"', name)

        self.Expression(self.choose(varterminal.expressions))
        retval = self.globals['_g_var']['$*']
        for decorator in varterminal.decorators:
            retval = self.__decorator(decorator)(retval)

        self.globals['_g_var']['$*'] = retval
        self.globals['_g_var']['$$'] = retval
        self.backref[name] = retval
        return retval

    def Terminal(self, value):
        return value

    def Backreference(self, name):
        return self.backref.get(name[1:], None)

    def Anonymous(self, anonterminal):
        retval = self.Expression(self.choose(anonterminal.expressions))
        return retval

    def Function(self, functionName, arguments):
        functionName = functionName[:-1]
        try:
            function = eval(functionName, self.globals)
        except NameError:
            raise nelly.error('Unknown function: %s', functionName)
        args = []
        for expression in arguments.expressions:
            args.append(self.Expression(expression))
        retval = function(*args)
        return retval

    def Reference(self, name):
        try:
            return eval(name, self.globals)
        except NameError:
            raise nelly.error('Unknown reference: &%s', name)

    def __ExecPython(self, pycode):
        try:
            exec(pycode, self.globals)
        except KeyError as e:
            name, = e.args
            if name[0] == '$':
                raise nelly.error('Undeclared variable "%s"', name[1:]) from None
            raise
        except SystemExit as e:
            return False if e.code else True

    def __decorator(self, name):
        try:
            return eval(name, self.globals)
        except NameError:
            raise nelly.error('Unknown decorator "%s"', name) from None

    LOOKUP = dict(enumerate((
        Terminal,
        Nonterminal,
        Varterminal,
        Backreference,
        Anonymous,
        Reference,
        Function,
        )))
