from pyspades.server import block_action
from pyspades.collision import distance_3d_vector
from commands import add, admin
from map import Map
from pyspades.constants import *
import commands

# requires box.py

def sign(x):
    return (x > 0) - (x < 0)

@admin
def wall(connection, value = None):
    value = int(value)
    if value < 65 and value > -63 and value != 0:
        connection.walling = value
        return 'Building %s block high wall. "/wall 0" to cancel.' % connection.walling
    else:
        connection.walling = None
        return 'No longer building wall. Must be /wall 64 or Less!'
add(wall)

def apply_script(protocol, connection, config):
    class WallMakerConnection(connection):
        walling = None
        def on_block_build(self, x, y, z):
            if self.walling is not None:
                self.build_box_filled(x, y, z, x, y, min(61, max(0, z - self.walling + sign(self.walling))), self.color+(255,))
            return connection.on_block_build(self, x, y, z)
    return protocol, WallMakerConnection
