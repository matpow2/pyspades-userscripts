""" Get a player's hp!

/hp <player name or id>

Author: infogulch
"""

from commands import get_player, add, InvalidPlayer, InvalidSpectator

def hp(connection, player_name):
    try:
        player = get_player(connection.protocol, player_name, False)
    except InvalidPlayer:
        return 'Invalid player'
    except InvalidSpectator:
        return 'Player is a spectator'
    
    return "%s's HP is: %i" % (player.name, player.hp)

add(hp)

def apply_script(protocol, connection, config):
    return protocol, connection