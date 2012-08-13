# avx.py
import array
import collections
import operator
import math
import io
import gzip
import os

from itertools import izip, imap, chain, ifilter, product, repeat
from struct import pack, unpack, calcsize

# this module is a self-contained pure python implementation of a generic AVX loader/saver

# AVX Header: magic "AVX" followed by a version byte. Then a version-specific header.
# Depending on the version and header, it will load fixed or variable sized voxel geometry 
#   and optionally color data for surface voxels.

# A voxel is surface IFF: 
#   it is solid AND (one of its neighbors is not solid OR it is on the edge)

# Note: This is probably a better implementation of bitarrays: http://pypi.python.org/pypi/bitarray#downloads

DEFAULT_COLOR =  (103, 64, 40)

class BitArray(object):
    _bits = 8
    _maxbit = _bits - 1
    _max = 2 ** _bits - 1
    _log = int(round(math.log(_bits, 2)))
    
    def __init__(self, bits, fill = 0):
        self.bits = int(bits)
        self.bit_array = array.array('B')
        
        if fill == 1:
            fill = self._max # all bits set
        else:
            fill = 0         # all bits cleared
        
        self.bit_array.extend((fill,) * self._array_size(self.bits))
    
    @classmethod
    def fromstring(cls, str, bits = -1):
        ret = cls(0)
        ret.loadstring(str, bits)
        return ret
    
    def loadstring(self, str, bits = -1):
        max_bits = len(str) * 8
        if bits > max_bits:
            raise ValueError()
        if bits < max_bits:
            str = str[:int(math.ceil(bits/8.0))]
        self.bit_array.fromstring(str)
        self.bits = max(bits, max_bits)
    
    @staticmethod
    def _array_size(bits):
        i = bits >> BitArray._log
        if (bits & BitArray._maxbit):
            i += 1       #    a record for stragglers
        return i
    
    def get(self, bit_num):
        record = bit_num >> self._log
        offset = bit_num & self._maxbit
        mask = 1 << offset
        return (self.bit_array[record] & mask) >> offset
    
    def set(self, bit_num):
        record = bit_num >> self._log
        offset = bit_num & self._maxbit
        mask = 1 << offset
        self.bit_array[record] |= mask
    
    def clear(self, bit_num):
        record = bit_num >> self._log
        offset = bit_num & self._maxbit
        mask = ~(1 << offset)
        self.bit_array[record] &= mask

    def toggle(self, bit_num):
        record = bit_num >> self._log
        offset = bit_num & self._maxbit
        mask = 1 << offset
        self.bit_array[record] ^= mask
    
    def tostring(self, padbytes = 1):
        # minimum padbytes == 1
        str = self.bit_array.tostring()
        str = str[:int(math.ceil(self.bits / 8.0))]
        str += '\x00' * (-len(str) % padbytes)
        return str

class BitArrayND(BitArray):
    def __init__(self, shape, fill=0):
        self.shape = shape
        BitArray.__init__(self, self.bits, fill)
    
    bits = property(lambda self: reduce(operator.mul, self.shape), lambda self, value: None)
    
    @classmethod
    def fromsparselist(cls, list):
        ret = cls((0,) * len(list[0]))
        ret.shape = [n+1 for n in map(max, izip(*list))]
        ret.bit_array.extend((0,) * ret._array_size(ret.bits))
        for coords in list:
            ret.set(coords)
        return ret
    
    @classmethod
    def fromstring(cls, shape, str):
        ret = cls((0,) * len(shape))
        ret.shape = shape
        BitArray.loadstring(ret, str, ret.bits)
        return ret
    
    def _ravel(self, coords):
        i = 0
        for dim, j in zip(self.shape, coords):
            i = i * dim + j
        return i
    
    def get(self, coords):
        return BitArray.get(self, self._ravel(coords))
    
    def set(self, coords):
        return BitArray.set(self, self._ravel(coords))
    
    def clear(self, coords):
        return BitArray.clear(self, self._ravel(coords))
    
    def toggle(self, coords):
        return BitArray.toggle(self, self._ravel(coords))
    
    def tosparselist(self):
        ret = []
        for coords in product(*map(xrange, self.shape)):
            if self.get(coords):
                ret.append(coords)
        return ret
    
    def isvalidcoords(self, coords):
        return all((n >= 0 and n < d for n, d in izip(coords, self.shape)))
    
    def neighbors(self, coords):
        'returns the coordinates of all the valid elements whose coordinates differ from `coords` by +-1 in any one dimension'
        if not self.isvalidcoords(coords):
            return
        i = 0
        for changed in map(sum,product(coords, (1, -1))):
            n = coords[:i//2] + (changed,) + coords[i//2+1:]
            if self.isvalidcoords(n):
                yield n
            i += 1

def open_gzip(file = None, fileobj = None):
    if fileobj is None:
        if not os.path.isfile(file) and os.path.isfile(file + '.gz'):
            file += '.gz'
        return open_gzip(fileobj = open(file, 'rb'))
    p = fileobj.tell()
    magic = unpack('H', fileobj.read(2))
    fileobj.seek(p, 0)
    if magic == 0x1F8B: # .gz magic
        fileobj = gzip.GzipFile(fileobj = fileobj)
    return fileobj

class AVX(BitArrayND):
    # headers [(attribute_name, struct.fmt)]
    avx_magic = [('magic', '3s'), ('ver', 'B')]
    avx_headers_ver = [
            [('size_x', 'H'), ('size_y', 'H'), ('size_z', 'H'), ('has_colors', '?'), ('pad_bytes', 'B')]
        ]
    
    magic = 'AVX'
    ver = 0
    
    def __init__(self, x, y, z, colored = True, default_color = DEFAULT_COLOR):
        BitArrayND.__init__(self, [x, y, z])
        self.has_colors = bool(colored)
        self.colors = dict()
        self.default_color = tuple(default_color)
        self.pad_bytes = 1
    
    @classmethod
    def fromsparselist(cls, list, colored = False, default_color = DEFAULT_COLOR):
        # a list of 1 bits coords in the form of [(x1,y1,z1), (x2,y2,z2)]
        parent = BitArrayND.fromsparselist(list)
        ret = cls(0, 0, 0, colored = colored, default_color = default_color) 
        ret.shape = parent.shape
        ret.bit_array = parent.bit_array
        if ret.has_colors:
            ret.colors = dict((xyz, ret.default_color) for xyz in product(*map(xrange, ret.shape)) if ret.issurface(xyz))
        return ret
    
    @classmethod
    def fromsparsedict(cls, dict, colored = True, default_color = DEFAULT_COLOR):
        # {(x1,y1,z1): color, (x2,y2,z2): None, ...}
        ret = cls.fromsparselist(dict.keys(), colored = colored, default_color = default_color)
        if ret.has_colors:
            for coords, color in dict.iteritems():
                ret.setcolor(coords, color)
        return ret
    
    @classmethod
    def fromfile(cls, file = None, fileobj = None):
        fileobj = open_gzip(file, fileobj)
        
        # new instance, load magic attributes
        ret = cls(0, 0, 0)
        ret._load_attributes(fileobj, cls.avx_magic)
        
        if ret.magic != cls.magic or ret.ver > cls.ver:
            raise IOError("Not an AVX file")
        
        ret._load_attributes(fileobj, ret.avx_headers_ver[ret.ver])
        
        bytes = int(math.ceil(ret.bits/8.0))
        bytes += -bytes % ret.pad_bytes
        ret.loadstring(fileobj.read(bytes), ret.bits)
        
        if ret.has_colors:
            #read at most x*y*z color tuples
            str = fileobj.read(3*reduce(operator.mul, ret.shape))
            i = 0
            for xyz in product(*map(xrange, ret.shape)):
                if ret.issurface(xyz):
                    ret.colors[xyz] = unpack('BBB', str[i:i+3])
                    i += 3
        
        return ret
    
    def _load_attributes(self, fileobj, attributes):
        # save the current position, seek to the end to get remaining size, seek back
        pos = fileobj.tell()
        fileobj.seek(0, 2)
        size = fileobj.tell()
        fileobj.seek(pos, 0)
        if size - pos < calcsize(''.join(zip(*attributes)[1])):
            raise EOFError("Incomplete AVX file.")
        
        for attr, fmt in attributes:
            setattr(self, attr, unpack(fmt, fileobj.read(calcsize(fmt)))[0])
    
    def save(self, file = None, fileobj = None, compresslevel = None):
        if fileobj is None:
            return self.save(fileobj = open(file, 'wb'))
        if compresslevel:
            return self.save(fileobj = GzipFile(fileobj = fileobj, compresslevel = compresslevel))
        
        for attr, fmt in chain(self.avx_magic, self.avx_headers_ver[self.ver]):
            fileobj.write(pack(fmt, getattr(self, attr)))
        
        fileobj.write(self.tostring(self.pad_bytes))
        
        if self.has_colors:
            for xyz in sorted(self.colors):
                fileobj.write(pack('BBB', *self.colors[xyz]))
    
    def props(n):
        def get(self): return self.shape[n]
        def set(self, value): self.shape[n] = value
        return get, set
    size_x, size_y, size_z = [property(*props(n)) for n in xrange(3)]
    del props
    
    def tosparsedict(self):
        return dict((coords, self.colors.get(coords, None)) for coords in self.tosparselist())
    
    def setcolor(self, coords, color):
        if self.has_colors and self.issurface(coords):
            self.colors[coords] = color
    
    def getcolor(self, coords):
        if self.has_colors and self.issurface(coords):
            return self.colors(coords)
    
    def fixcolors(fn):
        def wrapper(self, coords):
            fn(self, coords)
            for coord in list(self.neighbors(coords)) + [coords]:
                c = self.colors.has_key(coord)
                s = self.issurface(coord)
                if c != s:
                    if c:
                        self.colors.discard(coord)
                    else:
                        self.colors[coord] = self.default_color
        
        return wrapper
    
    @fixcolors
    def set(self, coords):
        BitArrayND.set(self, coords)
    
    @fixcolors
    def clear(self, coords):
        BitArrayND.clear(self, coords)
    
    @fixcolors
    def toggle(self, coords):
        BitArrayND.toggle(self, coords)
    
    del fixcolors
    
    def issurface(self, coords):
        return self.get(coords) and (
            any(a == 0 or a == n-1 for a,n in izip(coords, self.shape)) # on the edge of the map
            or not all(imap(self.get, self.neighbors(coords)))) # one of it neighbors is missing
#