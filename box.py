from pyspades.contained import BlockLine, SetColor
from pyspades.collision import distance_3d_vector
from pyspades.common import make_color
from pyspades.constants import *
from commands import add, admin
from itertools import product

from feature_server.scripts.cbc import *

# !! Dependent on script "cbc" being listed before this script

# todo: to all box,floor,db,df: kill modes when switching maps

def ordered_product(ranges, order):
    """Iterates through ranges in the order specified in order, but each yeild returns in the original order of the ranges"""
    
    order_inv = zip(*sorted(zip(order, sorted(order))))[1]
    
    for prod in product(*(ranges[o] for o in order)):
        yield tuple(prod[o] for o in order_inv)

MAX_LINE_BLOCKS = 64

@admin
def box(connection, filled = ""):
        if connection.boxing > 0:
            connection.boxing = 0
            return 'Building generator cancelled'
        else:
            connection.boxing = 1
            connection.boxing_filled = filled.lower() == "filled"
            return 'Place first corner block'
add(box)

def apply_script(protocol, connection, config):
    class BoxMakerConnection(connection):
        boxing = 0
        boxing_filled = 0
        box_x = 0
        box_y = 0
        box_z = 0
        
        def build_box_filled_generator(self, x1, y1, z1, x2, y2, z2, boxcolor):
            line = BlockLine()
            line.player_id = self.player_id
            # line.value = BUILD_BLOCK
            
            protocol = self.protocol
            check_protected = hasattr(protocol, 'protected')
            if self.god_build and protocol.god_blocks is None:
                protocol.god_blocks = set()
            
            ranges = [xrange(min(x1 , x2) , max(x1 , x2)+1)
                    , xrange(min(y1 , y2) , max(y1 , y2)+1)
                    , xrange(min(z1 , z2) , max(z1 , z2)+1)]
            
            order = zip(*sorted(zip([len(x) for x in ranges], [0, 1, 2])))[1]
            
            # set the first block position
            prod = ordered_product(ranges, order)
            line.x1, line.y1, line.z1 = prod.next()
            line.x2 = line.x1
            line.y2 = line.y1
            line.z2 = line.z1
            
            for x, y, z in prod:
                packets = 0
                if not self.god and check_protected and protocol.is_protected(x, y, z):
                    continue
                if self.god_build:
                    protocol.god_blocks.add((x, y, z))
                changed = (line.x1 != x or line.x2 != x) + (line.y1 != y or line.y2 != y) + (line.z1 != z or line.z2 != z)
                dist = abs(line.x1 - x) + abs(line.y1 - y) + abs(line.z1 - z)
                if changed > 1 or dist >= MAX_LINE_BLOCKS:
                    protocol.send_contained(line)
                    packets += 1
                    line.x1 = x
                    line.y1 = y
                    line.z1 = z
                line.x2 = x
                line.y2 = y
                line.z2 = z
                protocol.map.set_point(x, y, z, boxcolor)
                
                yield packets, 0
            protocol.send_contained(line)
            yield 1, 0
        
        def build_box_filled(self, x1, y1, z1, x2, y2, z2, boxcolor):
            if (x1 < 0 or x1 >= 512 or y1 < 0 or y1 >= 512 or z1 < 0 or z1 > 64 or
                x2 < 0 or x2 >= 512 or y2 < 0 or y2 >= 512 or z2 < 0 or z2 > 64):
                return 'Invalid coordinates'
            self.protocol.cbc_add(self.build_box_filled_generator(x1, y1, z1, x2, y2, z2, boxcolor))
        
        def build_box(self, x1, y1, z1, x2, y2, z2, boxcolor):
            self.build_box_filled(x1, y1, z1, x1, y2, z2, boxcolor)
            self.build_box_filled(x2, y1, z1, x2, y2, z2, boxcolor)
            self.build_box_filled(x1, y1, z1, x2, y1, z2, boxcolor)
            self.build_box_filled(x1, y2, z1, x2, y2, z2, boxcolor)
            self.build_box_filled(x1, y1, z1, x2, y2, z1, boxcolor)
            self.build_box_filled(x1, y1, z2, x2, y2, z2, boxcolor)
        
        def on_block_build(self, x, y, z):
            if self.boxing == 2:
                self.boxing = 0
                if self.boxing_filled == 0:
                    self.build_box(self.box_x, self.box_y, self.box_z, x, y, z, self.color+(255,))
                else:
                    self.build_box_filled(self.box_x, self.box_y, self.box_z, x, y, z, self.color+(255,))
                self.send_chat('Box created!')
            if self.boxing == 1:
                self.box_x = x
                self.box_y = y
                self.box_z = z
                self.send_chat('Now place opposite corner block')
                self.boxing = 2
            return connection.on_block_build(self, x, y, z)
    
    class BoxMakerProtocol(protocol):
        def on_map_change(self, map):
            for connection in self.clients:
                connection.boxing = 0
            protocol.on_map_change(self, map)
    
    return BoxMakerProtocol, BoxMakerConnection