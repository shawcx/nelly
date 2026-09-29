#!/usr/bin/env python3
#
# (c) 2008-2021 Matthew Shaw
#

import sys
import os
import argparse
import time
import logging

import nelly


# consecutive fail() calls before giving up
MAX_FAILURES = 1000


class Output:
    def __init__(self, path, hexdump):
        self.path    = path
        self.hexdump = hexdump
        self.fp      = None
        if path and path != '-' and '%' not in path:
            self.fp = self._open(path)

    def Write(self, result, count):
        if result is None or not (self.path or self.hexdump):
            return
        try:
            data = nelly.tobytes(result)
        except TypeError:
            raise nelly.error('Cannot output a result of type %s', type(result).__name__) from None

        if self.hexdump:
            nelly.hexdump(data)
            print()

        if self.path == '-':
            # flush anything printed by the grammar before writing raw bytes
            sys.stdout.flush()
            sys.stdout.buffer.write(data)
            sys.stdout.buffer.flush()
        elif self.fp:
            self.fp.write(data)
        elif self.path:
            with self._open(self.path % count) as fp:
                fp.write(data)

    def Close(self):
        if self.fp:
            self.fp.close()

    def _open(self, path):
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        try:
            return open(path, 'wb')
        except OSError as e:
            raise nelly.error('Could not open output: %s', e) from None


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    argparser = argparse.ArgumentParser()

    argparser.add_argument('grammar',
        nargs='?', default=None,
        help='Input file')

    argparser.add_argument('--start', '-s',
        action='append',
        help='Specify the starting point')

    argparser.add_argument('--count', '-c',
        type=int, default=1,
        help='Number of results to generate, 0 for no limit')

    argparser.add_argument('--include', '-i',
        action='append', default=['.'],
        help='Include path')

    argparser.add_argument('--vars', '-v',
        action='append',
        help='Variables to set')

    argparser.add_argument('--encode', '-e',
        help='Set the encoding to use for binary data')

    argparser.add_argument('--dictionary', '-d',
        help='Output an AFL dictionary file')

    argparser.add_argument('--output', '-o',
        help='Write each result as bytes: - for stdout, a path with %%d for '
             'one file per result, or a path for all results in one file')

    argparser.add_argument('--hexdump', '-x',
        action='store_true',
        help='Print a hexdump of each result')

    argparser.add_argument('--debug', '-D',
        action='store_true',
        help='Enable debug logging')

    args = argparser.parse_args(argv)

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
            if '=' not in var:
                argparser.error('--vars expects KEY=VALUE, got %r' % var)
            name,value = var.split('=', 1)
            name = '$'+name
            variables[name] = value

    try:
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
                raise nelly.error('Could not open grammar: %s', path) from None

        parser = nelly.Parser(includes)
        try:
            program = parser.Parse(grammarFile)
        finally:
            if grammarFile is not sys.stdin:
                grammarFile.close()

        if args.start:
            program.start = args.start

        if args.dictionary:
            dictionary = nelly.Dictionary(args.dictionary)
            dictionary.Walk(program)
        else:
            logging.debug('Executing program')
            output = Output(args.output, args.hexdump)
            count = 0
            failures = 0
            t1 = time.time()
            try:
                while args.count <=0 or count < args.count:
                    sandbox = nelly.Sandbox(variables)
                    try:
                        output.Write(sandbox.Execute(program), count)
                    except SystemError:
                        # fail() discards the result, try again with the same $count
                        logging.debug('Script called fail()')
                        failures += 1
                        if failures == MAX_FAILURES:
                            logging.error('fail() called %d times in a row, stopping', failures)
                            break
                        continue
                    except SystemExit:
                        logging.warning('Script called bail()')
                        break
                    except nelly.error as e:
                        logging.error('%s', e)
                        break
                    failures = 0
                    count += 1
                    variables['$count'] = count
            except KeyboardInterrupt:
                pass
            finally:
                output.Close()
            t2 = time.time()

            elapsed = t2 - t1
            rate    = count / elapsed if elapsed > 0 else 0.0
            logging.info('Ran %d iterations in %.2f seconds (%.2f tps)', count, elapsed, rate)
    except nelly.error as e:
        logging.error('%s', e)
        return -1

    return 0
