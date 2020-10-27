#
# (c) 2008-2020 Matthew Shaw
#

import sys


def bail():
    raise SystemExit from None


def fail():
    raise SystemError from None


def hexdump(blob, width=16, offset=0):
    fmt = '%%.%dx: ' % len('%.x' % (len(blob) - 1))
    while blob:
        line = bytearray(blob[:width])
        blob = blob[width:]

        sys.stdout.write(fmt % offset)
        sys.stdout.write(' '.join('%.2x' % c for c in line))
        sys.stdout.write(' ' * ((width-len(line))*3+1))

        for c in line:
            if c < 32 or c > 126:
                sys.stdout.write('.')
            else:
                sys.stdout.write('%c' % c)

        sys.stdout.write('\n')
        offset += width
