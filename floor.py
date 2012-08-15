from commands import add, admin
import buildbox
import cbc

# requires buildbox.py script in the /scripts folder

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
    protocol, connection = cbc.apply_script(protocol, connection, config)
    
    class FloorMakerConnection(connection):
        def __init__(self, *arg, **kw):
            connection.__init__(self, *arg, **kw)
            self.flooring = 0
            self.floor_x = 0
            self.floor_y = 0
            self.floor_z = 0
        
        def on_block_build(self, x, y, z):
            if self.flooring == 2:
                self.flooring = 0
                if self.floor_z != z:
                    self.send_chat('Surface is uneven! Using first height.')
                buildbox.build_filled(self.protocol
                    , self.floor_x, self.floor_y, self.floor_z
                    , x, y, self.floor_z
                    , self.color, self.god, self.god_build)
            if self.flooring == 1:
                self.floor_x = x
                self.floor_y = y
                self.floor_z = z
                self.send_chat('Now place opposite corner block')
                self.flooring = 2
            return connection.on_block_build(self, x, y, z)
    
    class FloorMakerProtocol(protocol):
        def on_map_change(self, map):
            for connection in self.clients:
                connection.flooring = 0
            protocol.on_map_change(self, map)
    
    return FloorMakerProtocol, FloorMakerConnection
