#
# (c) 2008-2016 Matthew Oertle
#

import sys
import inspect
import struct


def Pack(basetype, fmt):
    '''
Pack(type, fmt) -> type

type: primitive type to be stored (e.g. int, str, float, long)
fmt: either format for struct.pack or a function to be applied

e.g.

>>> DWORD = Pack(int, 'I')
>>> print repr(DWORD(0x6162))
'ba\x00\x00'
>>> SSL = Pack(int, lambda s: struct.pack('!I', s)[:-3])
>>> print repr(SSL(0x6162))
'\x00\x00a'
    '''

    class __P(object):
        def _pack1(self):   return self.fmt(self)
        def _pack2(self):   return struct.pack(self.fmt, self)
        def __len__(self):  return struct.calcsize(self.fmt)
        def __str__(self):  return self._pack()
        def __repr__(self): return self._pack().__repr__()

    if inspect.isfunction(fmt):
        pack = __P._pack1
        fmt = staticmethod(fmt)
    else:
        pack = __P._pack2

    return type('#'+basetype.__name__, (__P, basetype), {'fmt': fmt, '_pack': pack})

BYTE   = Pack(int, 'B')
WORD   = Pack(int, 'H')
DWORD  = Pack(int, 'I')
QWORD  = Pack(int, 'Q')

LBYTE  = Pack(int, '<B')
LWORD  = Pack(int, '<H')
LDWORD = Pack(int, '<I')
LQWORD = Pack(int, '<Q')

BBYTE  = Pack(int, '>B')
BWORD  = Pack(int, '>H')
BDWORD = Pack(int, '>I')
BQWORD = Pack(int, '>Q')
