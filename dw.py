from pyspades.server import block_action
from pyspades.collision import distance_3d_vector
from commands import add, admin
from map import Map
from pyspades.constants import *
import commands

# requires db.py

def sign(x):
    return (x > 0) - (x < 0)

@admin
def dw(connection, value = None):
    value = int(value)
    if value < 65 and value > -63 and value != 0:
        connection.dewalling = value
        return 'DeWalling %s block high wall. "/dw 0" to cancel.' % connection.dewalling
    else:
        connection.dewalling = None
        return 'No longer DeWalling. Type /dw 64 or less.'
add(dw)

def apply_script(protocol, connection, config):
    class DeWallMakerConnection(connection):
        dewalling = None
        def on_block_removed(self, x, y, z):
            if self.dewalling is not None:
                self.clear_box_solid(x, y, z, x, y, min(61, max(0, z - self.dewalling + sign(self.dewalling))))
            return connection.on_block_removed(self, x, y, z)
    return protocol, DeWallMakerConnection
