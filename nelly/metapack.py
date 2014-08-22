
import struct

class Packer(type):
	class Pack:
		def pack(self):
			return struct.pack(self.fmt, self)
	
	def __new__(self, supertype, pack):
		dict = {'fmt': pack}
		name = 'Packer' + supertype.__name__
		return type.__new__(self, name, (supertype,Packer.Pack), dict)

	def __init__(self, supertype, pack):
		return type.__init__(self, supertype)

BYTE  = Packer(int, 'B')
WORD  = Packer(int, 'H')
DWORD = Packer(int, 'I')
QWORD = Packer(int, 'Q')

LBYTE  = Packer(int, '<B')
LWORD  = Packer(int, '<H')
LDWORD = Packer(int, '<I')
LQWORD = Packer(int, '<Q')

BBYTE  = Packer(int, '>B')
BWORD  = Packer(int, '>H')
BDWORD = Packer(int, '>I')
BQWORD = Packer(int, '>Q')
