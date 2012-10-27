"""
removesquad.py

Removes a player from their current squad, if any.
Useful in conjunction with the jail script.

REQUIRES SQUAD.PY
"""

from commands import admin, name, get_player, add

@admin
@name('rs')
def remove_squad(self, player_name):
    player = get_player(self.protocol, player_name)
    
    if player.squad is not None:
        player.squad = None
        player.squad_pref = None
        player.join_squad(None, None)
        return 'Removed player %s from their squad.' % player.name
    else:
        return 'Player %s is not in a squad!' % player.name

add(remove_squad)

def apply_script(protocol, connection, config):
    return protocol, connection
