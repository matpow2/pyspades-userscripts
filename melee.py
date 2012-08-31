"""
Melee game mode.

Toggle with command: /melee

Melee kills only. Guns and grenades are disabled.
Holding a block shields you from melee attacks except when you're holding the enemy's intel.
"""

from pyspades.server import orientation_data, weapon_reload
from pyspades.constants import *
from commands import add, admin, name

@admin
@name('melee')
def meleetoggle(connection):
    protocol = connection.protocol
    protocol.melee_mode = not protocol.melee_mode
    connection.send_chat("Melee is %s" % ['off', 'on'][protocol.melee_mode])

add(meleetoggle)

def apply_script(protocol, connection, config):
    class MeleeProtocol(protocol):
        def __init__(self, *arg, **kw):
            protocol.__init__(self, *arg, **kw)
            self.melee_mode = True
    
    class MeleeConnection(connection):
        def on_hit(self, hit_amount, hit_player, type, grenade):
            if self.protocol.melee_mode and (type != MELEE_KILL or (hit_player.tool == BLOCK_TOOL and hit_player.has_intel == False)):
                return False
            return connection.on_hit(self, hit_amount, hit_player, type, grenade)
        
        def on_grenade(self, time_left):
            if self.protocol.melee_mode:
                return False
        
        def on_flag_capture(self):
            self.has_intel = False
            return connection.on_flag_capture(self)
        
        def on_flag_drop(self):
            self.has_intel = False
            return connection.on_flag_drop(self)
        
        def on_flag_take(self):
            self.has_intel = True
            return connection.on_flag_take(self)
        
        def on_join(self):
            self.has_intel = False
            return connection.on_join(self)
        
        def on_spawn(self, pos):
            if self.protocol.melee_mode:
                self.clear_ammo()
        
        def on_refill(self):
            if not self.protocol.melee_mode:
                weapon_reload.player_id = self.player_id
                weapon_reload.clip_ammo = self.weapon_object.current_ammo
                weapon_reload.reserve_ammo = self.weapon_object.current_stock
                self.send_contained(weapon_reload)

                self.weapon_object.reload()
            return connection.on_refill(self)

        # clear_ammo() method by infogulch
        def clear_ammo(self):
            weapon_reload.player_id = self.player_id
            weapon_reload.clip_ammo = 0
            weapon_reload.reserve_ammo = 0
            self.grenades = 0
            self.weapon_object.clip_ammo = 0
            self.weapon_object.reserve_ammo = 0
            self.send_contained(weapon_reload)
    
    return MeleeProtocol, MeleeConnection
