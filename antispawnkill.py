"""
Anti-spawnkill.

Usage: /ask <seconds for a player to be invulnerable>
I'm capping it at 5 by default so people don't accidentally make everyone invincible.
"""
from time import time
from commands import add, admin, name

MAX_SECS_NODAMAGE = 5

@admin
@name('ask')
def antispawnkill(connection, seconds):
    protocol = connection.protocol
    protocol.ask_time = seconds if seconds <= MAX_SECS_NODAMAGE else MAX_SECS_NODAMAGE
    connection.send_chat("Anti-spawnkill time set to %s seconds" % protocol.ask_time)

add(antispawnkill)

def apply_script(protocol, connection, config):
    class ASKProtocol(protocol):
        def __init__(self, *arg, **kw):
            self.ask_time = 0
            protocol.__init__(self, *arg, **kw)
    
    class ASKConnection(connection):
        spawn_time = 0
        def on_hit(self, hit_amount, hit_player, type, grenade):
            if int( time() ) - hit_player.spawn_time < self.protocol.ask_time:
                return False
            return connection.on_hit(self, hit_amount, hit_player, type, grenade)
        
        def on_spawn(self, pos):
            self.spawn_time = int( time() )
            return connection.on_spawn(self, pos)

    return ASKProtocol, ASKConnection
