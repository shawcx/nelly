#!/usr/bin/env python3
#
# (c) 2008-2021 Matthew Shaw
#

"""Command line interface: parse a grammar and generate results from it."""

import argparse
import itertools
import logging
import os
import sys
import time

import nelly

log = logging.getLogger(__name__)

# consecutive fail() calls before giving up
MAX_FAILURES = 1000


def key_value(text):
    """argparse type for KEY=VALUE."""
    key, sep, value = text.partition('=')
    if not key or not sep:
        raise argparse.ArgumentTypeError('expected KEY=VALUE, got %r' % text)
    return key, value


def build_parser():
    parser = argparse.ArgumentParser(prog='nelly', description='A grammar-based test case generator.')
    parser.add_argument('grammar', nargs='?', default='-',
        help='grammar file (default: read from stdin)')
    parser.add_argument('-s', '--start', action='append',
        help='entry point to use instead of those marked start; may be repeated')
    parser.add_argument('-c', '--count', type=int, default=1,
        help='number of results to generate, 0 for no limit (default: 1)')
    parser.add_argument('-i', '--include', action='append', default=[],
        help='directory to search for included grammars; may be repeated')
    parser.add_argument('-v', '--vars', action='append', type=key_value, default=[], metavar='KEY=VALUE',
        help='set the variable $KEY; may be repeated')
    parser.add_argument('-e', '--encode', metavar='ENCODING',
        help='encode text with ENCODING and build every value as bytes')
    parser.add_argument('-d', '--dictionary', metavar='FILE',
        help='write an AFL dictionary instead of generating')
    parser.add_argument('-o', '--output', metavar='PATH',
        help='write each result as bytes: - for stdout, a path with %%d for '
             'one file per result, or a path for all results in one file')
    parser.add_argument('-x', '--hexdump', action='store_true',
        help='print a hexdump of each result')
    parser.add_argument('-D', '--debug', action='store_true',
        help='enable debug logging')
    return parser


def load_program(path, includes):
    """Parse the grammar at path, or stdin for '-'."""
    parser = nelly.Parser(includes)
    if path == '-':
        log.info('Reading from stdin')
        return parser.Parse(sys.stdin)

    path = os.path.abspath(os.path.expanduser(path))
    # let the grammar import Python modules that sit next to it
    sys.path.insert(0, os.path.dirname(path))
    try:
        fp = open(path)
    except OSError as e:
        raise nelly.error('Could not open grammar: %s: %s', path, e.strerror) from None
    with fp:
        return parser.Parse(fp)


def generate(program, variables, count):
    """Yield (index, result) for each result kept.

    Stops after count results (no limit if count <= 0) or when the grammar
    calls bail(). A result discarded with fail() is retried with the same
    index, up to MAX_FAILURES times in a row.
    """
    indices = range(count) if count > 0 else itertools.count()
    for index in indices:
        for _ in range(MAX_FAILURES):
            sandbox = nelly.Sandbox({**variables, '$count': index})
            try:
                result = sandbox.Execute(program)
            except SystemError:
                log.debug('Script called fail()')
                continue
            except SystemExit:
                log.warning('Script called bail()')
                return
            break
        else:
            raise nelly.error('fail() called %d times in a row, stopping', MAX_FAILURES)
        yield index, result


class Output:
    """Writes results as bytes to stdout, one file per result, or one file."""

    def __init__(self, path=None, hexdump=False):
        self.path    = path
        self.hexdump = hexdump
        self._file   = None

    def __enter__(self):
        if self.path and self.path != '-' and '%' not in self.path:
            self._file = self._open(self.path)
        return self

    def __exit__(self, *exc):
        if self._file:
            self._file.close()

    def write(self, result, index):
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
        elif self._file:
            self._file.write(data)
        elif self.path:
            with self._open(self.path % index) as fp:
                fp.write(data)

    @staticmethod
    def _open(path):
        directory = os.path.dirname(path)
        try:
            if directory:
                os.makedirs(directory, exist_ok=True)
            return open(path, 'wb')
        except OSError as e:
            raise nelly.error('Could not open output: %s', e) from None


def run(program, args):
    variables = {'$' + key: value for key, value in args.vars}
    produced = 0
    started  = time.perf_counter()
    try:
        with Output(args.output, args.hexdump) as output:
            for index, result in generate(program, variables, args.count):
                output.write(result, index)
                produced += 1
    except KeyboardInterrupt:
        pass
    finally:
        elapsed = time.perf_counter() - started
        rate    = produced / elapsed if elapsed > 0 else 0.0
        log.info('Ran %d iterations in %.2f seconds (%.2f tps)', produced, elapsed, rate)


def main(argv=None):
    args = build_parser().parse_args(argv)

    logging.basicConfig(
        format  = '%(asctime)s %(levelname)-8s %(message)s',
        datefmt = '%Y-%m-%d %H:%M:%S',
        level   = logging.DEBUG if args.debug else logging.INFO,
        )

    nelly.encode = args.encode

    try:
        program = load_program(args.grammar, ['.'] + args.include)
        if args.start:
            program.start = args.start

        if args.dictionary:
            nelly.Dictionary(args.dictionary).Walk(program)
        else:
            run(program, args)
    except nelly.error as e:
        log.error('%s', e)
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
