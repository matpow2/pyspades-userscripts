from commands import add, admin
import clearbox
import cbc

# requires clearbox.py in the /scripts directory

def sign(x):
    return (x > 0) - (x < 0)

@admin
def dw(connection, value = ''):
    try:
        value = int(value)
    except ValueError:
        value = 0
    if value < 65 and value > -65 and abs(value) > 1:
        connection.dewalling = value
        return 'DeWalling %s block high wall. "/dw" to cancel.' % connection.dewalling
    else:
        connection.dewalling = None
        return 'No longer DeWalling. Activate with `/dw 64` to `/dw -64`'
add(dw)

def apply_script(protocol, connection, config):
    protocol, connection = cbc.apply_script(protocol, connection, config)
    
    class DeWallMakerConnection(connection):
        def __init__(self, *args, **kwargs):
            connection.__init__(self, *args, **kwargs)
            self.dewalling = None
        
        def on_block_removed(self, x, y, z):
            if self.dewalling is not None:
                z2 = min(61, max(0, z - self.dewalling + sign(self.dewalling)))
                clearbox.clear_solid(self.protocol, x, y, z, x, y, z2, self.god)
            return connection.on_block_removed(self, x, y, z)
    
    return protocol, DeWallMakerConnection
