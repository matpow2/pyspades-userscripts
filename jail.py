"""
Jail script by PXYC

/jail <player> [reason] jails a player. Default reason is "None"
/free <player> frees a player.
/jailed [player] checks if a player is jailed. If no arguments are entered, it lists jailed players.
/jailbreak frees all jailed players.
"""

from pyspades.common import to_coordinates, coordinates
from commands import add, admin, get_player, join_arguments, name, alias
from pyspades.constants import *

jail_location = 0, 0, 0 # x, y, z of the jail
jail_coords   = [ ] # e.g. ["B4", "B5"]

jail_list = []

@name('jail')
@alias('j')
@admin
def jail_player(connection, value = None, *args):
    protocol = connection.protocol # Meh
    player = get_player(protocol, value) # Get player
    reason = join_arguments(args[0:]) # Convert reason args into one string
    if player not in protocol.players:
        raise ValueError() # If player doesn't exist, raise error
    else:
        if player.jailed:
            return 'Player ' + player.name + ' is already jailed!' # Player is already jailed!
        elif not player.jailed:
            player.jailed = True # Set player to jailed
            player.reason = reason
            player.set_location(jail_location) # Move player to jail
            connection.protocol.send_chat("%s was sent to jail by %s for reason(s): %s" % (player.name, connection.name, reason)) # Message
            connection.protocol.irc_say("* %s jailed %s for reason: %s" % (connection.name, player.name, reason)) # Message
            jail_list.append(player.name)
add(jail_player) # Add command

@name('jailed')
def is_jailed(connection, value = None):
    if value is None:
        if not jail_list:
            return 'No jailed players.'
        else:
            return "Jailed players: " + ", ".join(jail_list)
    elif value is not None:
        protocol = connection.protocol
        player = get_player(protocol, value)
        if player not in protocol.players:
            raise ValueError()
        else:
            if player.jailed:
                return 'Player %s jailed for: %s' % (player.name, player.reason)
            else:
                return 'Player %s is not jailed.' % (player.name)
add(is_jailed)

@name('free')
@admin
def free_from_jail(connection, value):
    protocol = connection.protocol # Meh
    player = get_player(protocol, value) # Get player
    if player not in protocol.players:
        raise ValueError() # Errors again
    else:
        if not player.jailed: # If player isn't jailed
            return 'Player ' + player.name + ' is not jailed!' # Message
        elif player.jailed: # If player is jailed
            player.jailed = False # Player is not jailed anymore
            player.kill() # Kill the player
            connection.protocol.send_chat("%s was freed from jail by %s" % (player.name, connection.name)) # Message
            connection.protocol.irc_say('* %s was freed from jail by %s' % (player.name, connection.name)) # Message
            jail_list.remove(player.name)

add(free_from_jail)

@name('jailbreak')
@admin
def free_all(connection):aa
    protocol = connection.protocol
    for playersJailed in jail_list:
        player = get_player(protocol, playersJailed)
        player.kill()
        player.jailed = False
        player.reason = None
        jail_list.remove(playersJailed)
    return 'All players freed.'

add(free_all)

def apply_script(protocol, connection, config):
    class JailConnection(connection):
        jailed = False
        def on_spawn_location(self, pos):
            if self.jailed:
                return jail_location
            return connection.on_spawn_location(self, pos)
        def on_block_build_attempt(self, x, y, z):
            x, y, z = self.get_location()
            coord = to_coordinates(x, y)
            if self.jailed:
                self.send_chat("You can't build when you're jailed! You were jailed for %s" % (self.reason))
                return False
            elif coord in jail_coords and not self.user_types.admin: # Stuff
                self.send_chat("You can't build near the jail, %s!" % self.name)
                return False
            return connection.on_block_build_attempt(self, x, y, z)
        def on_block_destroy(self, x, y, z, mode):
            x, y, z = self.get_location()
            coord = to_coordinates(x, y)
            if self.jailed:
                self.send_chat("You can't destroy blocks when you're in jail! You were jailed for: %s" % (self.reason))
                return False
            elif coord in jail_coords and not self.user_types.admin:
                self.send_chat("Stop trying to destroy the jail, %s!" % self.name)
                return False
            return connection.on_block_build_attempt(self, x, y, z)
        def on_line_build_attempt(self, points):
            x, y, z = self.get_location()
            coord = to_coordinates(x, y)
            if self.jailed:
                self.send_chat("You can't build when you're jailed! You were jailed for: %s" % (self.reason))
                return False
            elif coord == in jail_coords and not self.user_types.admin:
                self.send_chat("You can't build near the jail, %s!" % self.name)
                return False
            return connection.on_line_build_attempt(self, points)
        def on_hit(self, hit_amount, player, type, grenade):
            if self.jailed:
                if self.name == player.name:
                    self.send_chat("Suicide isn't an option!")
                    return False
                else:
                    self.send_chat("You can't hit people when you're jailed! You were jailed for: %s" % (self.reason))
                    return False
            return connection.on_hit(self, hit_amount, player, type, grenade)
        def on_disconnect(self):
            if self.jailed:
                jail_list.remove(self.name)
                self.jailed = False
            return connection.on_disconnect(self)
    return protocol, JailConnection
