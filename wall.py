from commands import add, admin
import buildbox
import cbc

# requires buildbox.py script in the /scripts folder

def sign(x):
    return (x > 0) - (x < 0)

@admin
def wall(connection, value = ''):
    try:
        value = int(value)
    except ValueError:
        value = 0
    if value < 65 and value > -65 and abs(value) > 1:
        connection.walling = value
        return 'Building %s block high wall. "/wall" to cancel.' % connection.walling
    else:
        connection.walling = None
        return 'No longer building wall. Activate with `/wall 64` to `/wall -64`'
add(wall)

def apply_script(protocol, connection, config):
    protocol, connection = cbc.apply_script(protocol, connection, config)
    
    class WallMakerConnection(connection):
        def __init__(self, *arg, **kw):
            connection.__init__(self, *arg, **kw)
            self.walling = None
        
        def on_block_build(self, x, y, z):
            if self.walling is not None:
                z2 = min(61, max(0, z - self.walling + sign(self.walling)))
                buildbox.build_filled(self.protocol, x, y, z, x, y, z2, self.color, self.god, self.god_build)
            return connection.on_block_build(self, x, y, z)
    
    return protocol, WallMakerConnection
