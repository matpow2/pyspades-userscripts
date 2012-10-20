"""
Anti-spawnkill.

Usage: /ask <seconds for a player to be invulnerable>
I'm capping it at 5 by default so people don't accidentally make everyone invincible.
"""
from time import time
from scheduler import Scheduler
from commands import add, admin, name
from pyspades.server import create_player, set_tool, set_color, input_data, weapon_input
from pyspades.common import make_color

MAX_SECS_NODAMAGE = 5

@admin
@name('ask')
def antispawnkill(connection, seconds):
    protocol = connection.protocol
    seconds = int(seconds)
    protocol.ask_time = seconds if seconds <= MAX_SECS_NODAMAGE else MAX_SECS_NODAMAGE
    connection.protocol.send_chat("Anti-spawnkill time set to %s seconds by %s" % ( protocol.ask_time, connection.name ), irc = True)

add(antispawnkill)

# Not the best solution, but it works. Just copied the normal inv function
# and removed anti-kill stuff.
def my_invisible(connection):
    protocol = connection.protocol

    player = connection

    player.invisible = not player.invisible
    player.filter_visibility_data = player.invisible

    if not player.invisible and player.world_object is not None:
        x, y, z = player.world_object.position.get()
        create_player.player_id = player.player_id
        create_player.name = player.name
        create_player.x = x
        create_player.y = y
        create_player.z = z
        create_player.weapon = player.weapon
        create_player.team = player.team.id

        world_object = player.world_object

        input_data.player_id = player.player_id
        input_data.up = world_object.up
        input_data.down = world_object.down
        input_data.left = world_object.left
        input_data.right = world_object.right
        input_data.jump = world_object.jump
        input_data.crouch = world_object.crouch
        input_data.sneak = world_object.sneak
        input_data.sprint = world_object.sprint

        set_tool.player_id = player.player_id
        set_tool.value = player.tool
        set_color.player_id = player.player_id
        set_color.value = make_color(*player.color)

        weapon_input.primary = world_object.primary_fire
        weapon_input.secondary = world_object.secondary_fire

        protocol.send_contained(create_player, sender = player, save = True)
        protocol.send_contained(set_tool, sender = player)
        protocol.send_contained(set_color, sender = player, save = True)
        protocol.send_contained(input_data, sender = player)
        protocol.send_contained(weapon_input, sender = player)

        player.send_chat("Now visible.")

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
            my_invisible(self)
            schedule = Scheduler(self.protocol)
            schedule.call_later(self.protocol.ask_time, self.uninvis)
            return connection.on_spawn(self, pos)

        def uninvis(self):
            my_invisible(self)

    return ASKProtocol, ASKConnection
