from pyspades.server import block_action
from pyspades.collision import distance_3d_vector
from commands import add, admin
from map import Map
from pyspades.constants import *
import commands

# requires box.py

@admin
def floor(connection):
        if connection.flooring > 0:
            connection.flooring = 0
            return 'Floor generator cancelled'
        else:
            connection.flooring = 1
            return 'Place first corner block'
add(floor)

def apply_script(protocol, connection, config):
    class floorMakerConnection(connection):
        flooring = 0
        floor_x = 0
        floor_y = 0
        floor_z = 0
        
        def on_block_build(self, x, y, z):
            if self.flooring == 2:
                self.flooring = 0
                if self.floor_z != z:
                    self.send_chat('Surface is uneven! Using first height.')
                self.build_box_filled(self.floor_x, self.floor_y, self.floor_z, x, y, self.floor_z, self.color+(255,))
            if self.flooring == 1:
                self.floor_x = x
                self.floor_y = y
                self.floor_z = z
                self.send_chat('Now place opposite corner block')
                self.flooring = 2
            return connection.on_block_build(self, x, y, z)

    return protocol, floorMakerConnection
