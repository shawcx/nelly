#!/usr/bin/env python3

#
# (c) 2008-2020 Matthew Shaw
#

import sys
import os
import argparse
import time
import logging

import nelly


def main(args=None):
    if args is None:
        args = sys.argv[1:]

    argparser = argparse.ArgumentParser()

    argparser.add_argument('grammar',
        nargs='?', default=None,
        help='Input file')

    argparser.add_argument('--start', '-s',
        action='append',
        help='Specify the starting point')

    argparser.add_argument('--count', '-c',
        type=int, default=1,
        help='Number of times to run')

    argparser.add_argument('--include', '-i',
        action='append', default=['.'],
        help='Include path')

    argparser.add_argument('--vars', '-v',
        action='append',
        help='Variables to set')

    argparser.add_argument('--encode', '-e',
        help='Set the encoding to use for binary data')

    argparser.add_argument('--debug', '-D',
        action='store_true',
        help='Enable debug logging')

    args = argparser.parse_args(args)

    nelly.encode = args.encode

    logging.basicConfig(
        format  = '%(asctime)s %(levelname)-8s %(message)s',
        datefmt = '%Y-%m-%d %H:%M:%S',
        level   = logging.DEBUG if args.debug else logging.INFO
        )

    includes = args.include

    variables = {'$count' : 0}
    if args.vars:
        for var in args.vars:
            name,value = var.split('=', 1)
            name = '$'+name
            variables[name] = value

    if args.grammar is None:
        logging.info('Reading from stdin')
        grammarFile = sys.stdin
    else:
        path = os.path.expanduser(args.grammar)
        path = os.path.abspath(path)
        # insert root directory for relative imports related to the grammar
        sys.path.insert(0, os.path.dirname(path))
        try:
            grammarFile = open(path, 'r')
        except IOError:
            raise nelly.error('Could not open grammar: %s', path)

    parser = nelly.Parser(includes)
    program = parser.Parse(grammarFile)

    if args.start:
        program.start = args.start

    logging.debug('Executing program')
    count = 0
    t1 = time.time()
    try:
        while args.count <=0 or count < args.count:
            sandbox = nelly.Sandbox(variables)
            try:
                sandbox.Execute(program)
            except SystemError:
                logging.warn('Script called fail()')
            except SystemExit:
                logging.warn('Script called bail()')
                break
            except nelly.error as e:
                logging.error('%s', e)
                break
            count += 1
            variables['$count'] = count
    except KeyboardInterrupt:
        pass
    t2 = time.time()

    logging.info('Ran %d iterations in %.2f seconds (%.2f tps)', count, t2 - t1, count / (t2 - t1))

    return 0


def entry():
    try:
        sys.exit(main())
    except nelly.error as e:
        logging.error('%s', e)
        sys.exit(-1)
