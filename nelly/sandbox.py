#
# (c) 2008-2020 Matthew Shaw
#

import sys
import os
import random
import logging

import nelly

from .types import *


class Sandbox:
    def __init__(self, variables=None):
        self.globals = {
            'nelly' : nelly,
        }
        self.globals['_g_var'] = {
            '$NT' : self.Nonterminal,
            '$VT' : self.Varterminal,
            '$BR' : self.Backreference,
            }
        if variables:
            self.globals['_g_var'].update(variables)
        self.backref = {}
        self.record  = []

    def choose(self, nonterminal):
        choice = 0
        target = random.random()
        totalWeight = sum(e.weight for e in nonterminal.expressions)
        distribution = [e.weight / totalWeight for e in nonterminal.expressions]
        for ratio in distribution:
            if target < ratio:
                break
            target -= ratio
            choice += 1
        self.record.append(choice)
        return nonterminal.expressions[choice]

    def Execute(self, program):
        self.program = program

        for pycode in self.program.preamble:
            ok = self.__ExecPython(pycode)
            if ok:
                raise nelly.error('SystemExit raised on preamble')

        if not self.program.start:
            raise nelly.error('No entry points')

        choice = random.randrange(len(self.program.start))
        self.record.append(choice)
        name = self.program.start[choice]

        if not name.startswith('$'):
            self.Nonterminal(name)
        else:
            self.Varterminal(name)

        for pycode in self.program.postscript:
            ok = self.__ExecPython(pycode)
            if ok:
                raise nelly.error('SystemExit raised on postscript')

        return self.globals['_g_var'].get('$$')

    def Expression(self, expression):
        retval = b'' if nelly.encode else ''

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

            if nelly.encode:
                if isinstance(current, str):
                    current = current.encode(nelly.encode)

            if retval:
                try:
                    retval += current
                except TypeError as e:
                    print(e)
                    raise nelly.error('TypeError at %s', expression.location) from None
            else:
                retval = current

        self.globals['_g_var']['$*'] = None
        self.globals['_g_var']['$$'] = retval

        if expression.code:
            ok = self.__ExecPython(expression.code)
            if ok == False:
                raise nelly.error('Terminating on semantic action')

        return retval

    def Nonterminal(self, name):
        try:
            nonterminal = self.program.nonterminals[name]
        except KeyError as e:
            raise nelly.error('Unknown nonterminal: "%s"', name) from None

        retval = self.Expression(self.choose(nonterminal))
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

        self.Expression(self.choose(varterminal))
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
        retval = self.Expression(self.choose(anonterminal))
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
        except Exception as e:
            logging.error('Unhandled exception in %s', pycode.co_filename[1:-1])
            logging.exception(e)
            return False

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
