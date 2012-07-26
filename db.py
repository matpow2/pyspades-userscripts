from pyspades.contained import BlockAction
from pyspades.collision import distance_3d_vector
from commands import add, admin
from map import Map
from pyspades.constants import *
from feature_server.scripts.cbc import *
import commands

@admin
def db(connection):
        if connection.deboxing > 0:
            connection.deboxing = 0
            return 'DeBox cancelled'
        else:
            connection.deboxing = 1
            return 'Break first corner block'
add(db)

def apply_script(protocol, connection, config):
    class ClearBoxMakerConnection(connection):
        deboxing = 0
        clearbox_x = 0
        clearbox_y = 0
        clearbox_z = 0
        
        def clear_box_solid_generator(self, x1, y1, z1, x2, y2, z2):
            block_action = BlockAction()
            block_action.value = DESTROY_BLOCK
            block_action.player_id = self.player_id
            protocol = self.protocol
            check_protected = hasattr(protocol, 'protected')
            for x in xrange(min(x1 , x2) , max(x1 , x2)+1):
                block_action.x = x
                for y in xrange(min(y1 , y2) , max(y1 , y2)+1):
                    block_action.y = y
                    for z in xrange(min(z1 , z2) , max(z1 , z2)+1):
                        if not self.god and check_protected and protocol.is_protected(x, y, z):
                            continue
                        if not self.god and protocol.god_blocks is not None and (x, y, z) in protocol.god_blocks:
                            continue
                        block_action.z = z
                        protocol.send_contained(block_action, save = True)
                        protocol.map.destroy_point(x, y, z)
                        yield 1, (x - min(x1, x2) + 0.0) / (abs(x1 - x2)+1)
        
        def clear_box_solid(self, x1, y1, z1, x2, y2, z2):
            if (x1 < 0 or x1 >= 512 or y1 < 0 or y1 >= 512 or z1 < 0 or z1 > 64 or
                x2 < 0 or x2 >= 512 or y2 < 0 or y2 >= 512 or z2 < 0 or z2 > 64):
                return 'Invalid coordinates'
            self.protocol.cbc_add(self.clear_box_solid_generator(x1, y1, z1, x2, y2, z2))
        
        def clear_box(self, x1, y1, z1, x2, y2, z2):
            # clear each face separately, the rest will fall
            self.clear_box_solid(x1, y1, z1, x1, y2, z2)
            self.clear_box_solid(x2, y1, z1, x2, y2, z2)
            
            self.clear_box_solid(x1, y1, z1, x2, y1, z2)
            self.clear_box_solid(x1, y2, z1, x2, y2, z2)
            
            self.clear_box_solid(x1, y1, z1, x2, y2, z1)
            self.clear_box_solid(x1, y1, z2, x2, y2, z2)
        
        def on_block_removed(self, x, y, z):
            if self.deboxing == 2:
                self.deboxing = 0
                self.clear_box(self.clearbox_x, self.clearbox_y, self.clearbox_z, x, y, z)
                self.send_chat('Box destroyed!')
            if self.deboxing == 1:
                self.clearbox_x = x
                self.clearbox_y = y
                self.clearbox_z = z
                self.send_chat('Now break opposite corner block')
                self.deboxing = 2
            return connection.on_block_removed(self, x, y, z)
    
    class ClearBoxMakerProtocol(protocol):
        def on_map_change(self, map):
            for connection in self.connections:
                connection.deboxing = 0
            protocol.on_map_change(self, map)
    
    return ClearBoxMakerProtocol, ClearBoxMakerConnection