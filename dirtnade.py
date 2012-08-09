"""
Makes grenades create blocks.

Maintainer: hompy
"""

from pyspades.server import block_action
from pyspades.constants import *
import cbc

DIRTNADE_BLOCKS = 19

def apply_script(protocol, connection, config):
    protocol, connection = cbc.apply_script(protocol, connection, config)
    
    def try_add_node(map, x, y, z, list):
        if x < 0 or x >= 512 or y < 0 or y >= 512 or z < 0 or z >= 62:
            return
        if map.get_solid(x, y, z):
            return
        list.append((x, y, z))
    
    class DirtGrenadeConnection(connection):
        def dirtnade_generator(self, x, y, z, blocks):
            map = self.protocol.map
            list = []
            try_add_node(map, x, y, z, list)
            block_action.value = BUILD_BLOCK
            block_action.player_id = self.player_id
            while list:
                x, y, z = list.pop(0)
                if connection.on_block_build_attempt(self, x, y, z) == False:
                    continue
                block_action.x = x
                block_action.y = y
                block_action.z = z
                self.protocol.send_contained(block_action, save = True)
                map.set_point(x, y, z, self.color)
                yield 1, 0
                blocks -= 1
                if blocks == 0:
                    break
                try_add_node(map, x, y, z - 1, list)
                try_add_node(map, x, y - 1, z, list)
                try_add_node(map, x, y + 1, z, list)
                try_add_node(map, x - 1, y, z, list)
                try_add_node(map, x + 1, y, z, list)
                try_add_node(map, x, y, z + 1, list)
            self.protocol.update_entities()
        
        def grenade_exploded(self, grenade):
            if self.name is None:
                return
            if self.weapon != 1:
                return connection.grenade_exploded(self, grenade)
            position = grenade.position
            x = int(position.x)
            y = int(position.y)
            z = int(position.z)
            self.protocol.cbc_add(self.dirtnade_generator(x, y, z, DIRTNADE_BLOCKS))
    
    return protocol, DirtGrenadeConnection