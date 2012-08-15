from commands import add, admin
import clearbox
import cbc

# requires clearbox.py in the /scripts directory

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
    protocol, connection = cbc.apply_script(protocol, connection, config)
    
    class ClearFloorMakerConnection(connection):
        def __init__(self, *args, **kwargs):
            connection.__init__(self, *args, **kwargs)
            self.deflooring = 0
            self.clearfloor_x = 0
            self.clearfloor_y = 0
            self.clearfloor_z = 0
        
        def on_block_removed(self, x, y, z):
            if self.deflooring == 2:
                self.deflooring = 0
                if self.clearfloor_z != z:
                    self.send_chat('Surface is uneven! Using first height.')
                clearbox.clear_solid(self.protocol, self.clearfloor_x, self.clearfloor_y, self.clearfloor_z, x, y, self.clearfloor_z, self.god)
                self.send_chat('Floor destroyed!')
            if self.deflooring == 1:
                self.clearfloor_x = x
                self.clearfloor_y = y
                self.clearfloor_z = z
                self.send_chat('Now break opposite corner block')
                self.deflooring = 2
            return connection.on_block_removed(self, x, y, z)
    
    class ClearFloorMakerProtocol(protocol):
        def on_map_change(self, map):
            for connection in self.clients:
                connection.deflooring = 0
            protocol.on_map_change(self, map)
    
    return ClearFloorMakerProtocol, ClearFloorMakerConnection
