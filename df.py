from pyspades.server import block_action
from pyspades.collision import distance_3d_vector
from commands import add, admin
from map import Map
from pyspades.constants import *
import commands

# requires db.py

@admin
def df(connection):
        if connection.deflooring > 0:
            connection.deflooring = 0
            return 'DeFloor cancelled'
        else:
            connection.deflooring = 1
            return 'Break first corner block'
add(df)

def apply_script(protocol, connection, config):
    class clearfloorMakerConnection(connection):
        deflooring = 0
        clearfloor_x = 0
        clearfloor_y = 0
        clearfloor_z = 0
        
        def on_block_removed(self, x, y, z):
            if self.deflooring == 2:
                self.deflooring = 0
                if self.clearfloor_z != z:
                    self.send_chat('Surface is uneven! Using first height.')
                self.clear_box_solid(self.clearfloor_x, self.clearfloor_y, self.clearfloor_z, x, y, self.clearfloor_z)
                self.send_chat('Floor destroyed!')
            if self.deflooring == 1:
                self.clearfloor_x = x
                self.clearfloor_y = y
                self.clearfloor_z = z
                self.send_chat('Now break opposite corner block')
                self.deflooring = 2
            return connection.on_block_removed(self, x, y, z)
                
    return protocol, clearfloorMakerConnection
