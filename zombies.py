from pyspades.server import orientation_data, grenade_packet, weapon_reload, set_tool
from pyspades.common import coordinates, Vertex3
from pyspades.world import Grenade
from commands import add, admin
from math import sin, floor, atan2
from pyspades.constants import *
from pyspades.server import block_action
from pyspades.collision import distance_3d
from twisted.internet.task import LoopingCall

HEAL_RATE = 1000

HUMAN = 1
ZOMBIE = 2
# ZOMBIE_HUMAN = HUMAN | ZOMBIE

S_ZOMBIE_VERSION  = 'Zombies 1.0.0 RC6 by Dany0'
S_ZOMBIE_HEALTH   = 'Zombie health is %i.'
S_ZOMBIE_TELEPORT = 'Zombies teleport %i blocks high.'
S_ZOMBIE_SPAWN    = 'Zombies spawn %i blocks high.'
S_ZOMBIE_STAT     = S_ZOMBIE_HEALTH + ' ' + S_ZOMBIE_TELEPORT + ' ' + S_ZOMBIE_SPAWN

@admin
def zhp(connection, value):
    if value == 0:
        a = True
    protocol = connection.protocol
    protocol.ZOMBIE_HP = abs(float(value))
    connection.send_chat(S_ZOMBIE_HEALTH % value)

@admin
def ztel(connection, value):
    protocol = connection.protocol
    protocol.ZOMBIE_TELEPORT = abs(int(value))
    connection.send_chat(S_ZOMBIE_TELEPORT % value)

@admin
def zspawnheight(connection, value):
    protocol = connection.protocol
    val = abs(int(value))
    if val >= 10:
        protocol.ZOMBIE_SPAWN_HEIGHT = val
        connection.send_chat(S_ZOMBIE_SPAWN % val)
    elif val < 10:
        protocol.ZOMBIE_SPAWN_HEIGHT = 0
        connection.send_chat('Disabling zombie spawning up in the air')
    return value

def zombiestat(connection):
    connection.send_chat(S_ZOMBIE_VERSION)
    connection.send_chat(S_ZOMBIE_STAT % (connection.protocol.ZOMBIE_HP, connection.protocol.ZOMBIE_TELEPORT))

add(ztel)
add(zhp)
add(zombiestat)
add(zspawnheight)

def apply_script(protocol, connection, config):
    class ZombiesProtocol(protocol):
        def __init__(self, *arg, **kw):
            protocol.__init__(self, *arg, **kw)
            self.ZOMBIE_TELEPORT = 17
            self.ZOMBIE_HP = 650
            self.ZOMBIE_SPAWN_HEIGHT = 0
    
    class ZombiesConnection(connection):
        mode = 0 #must be a class instance variable to overload refill()
        
        def on_spawn(self, pos):
            if self.team is self.protocol.green_team:
                # once spawned, human-zombies turn back into zombies
                self.mode = ZOMBIE
                self.can_heal = False
                self.health_message = False
                self.quickbuild_allowed = False
                self.clear_ammo()
                
                ## this makes zombies appear to have a weapon when they have a block
                # set_tool.player_id = self.player_id
                # set_tool.value = SPADE_TOOL
                # self.protocol.send_contained(set_tool, sender = self)
                
                if self.protocol.ZOMBIE_SPAWN_HEIGHT > 0:
                    player_location = self.world_object.position
                    loc = (player_location.x, player_location.y, player_location.z - self.protocol.ZOMBIE_SPAWN_HEIGHT)
                    self.set_location_safe(loc)
            else:
                self.mode = HUMAN
                self.can_heal = True
                self.health_message = True
                self.quickbuild_allowed = True
            return connection.on_spawn(self, pos)
        
        def create_explosion_effect(self, position):
            self.protocol.world.create_object(Grenade, 0.1, position, None, Vertex3(), None)
            grenade_packet.value = 0.0
            grenade_packet.player_id = 32
            grenade_packet.position = position.get()
            grenade_packet.velocity = (0.0, 0.0, 0.0)
            self.protocol.send_contained(grenade_packet)
        
        def on_line_build_attempt(self, points):
            if self.mode == ZOMBIE:
                return False
            return connection.on_line_build_attempt(points)
        
        def on_block_build_attempt(self, x, y, z):
            if self.mode == ZOMBIE:
                return False
            return connection.on_block_build_attempt(self, x, y, z)
        
        def on_block_destroy(self, x, y, z, value):
            if (self.mode == ZOMBIE and value == DESTROY_BLOCK and self.tool == SPADE_TOOL):
                    map = self.protocol.map
                    ztel = self.protocol.ZOMBIE_TELEPORT
                    if (not map.get_solid(x, y, z-ztel+1) and not map.get_solid(x, y, z-ztel+2) and not map.get_solid(x, y, z-ztel+3)): 
                        player_location = self.world_object.position
                        self.create_explosion_effect(player_location)
                        loc = (player_location.x, player_location.y, player_location.z-ztel)
                        self.set_location(loc)
            return connection.on_block_destroy(self, x, y, z, value)
        
        def on_flag_capture(self):
            if self.team is self.protocol.green_team:
                self.mode = HUMAN
                self.refill()
                self.send_chat('YOU ARE HUMAN NOW RAWR GO SHOOT EM')
                self.protocol.send_chat('%s has become a human-zombie and can use weapons!' % self.name)
            return connection.on_flag_capture(self)
        
        def on_flag_take(self):
            if self.team is self.protocol.blue_team:
                self.set_hp(self.hp*2)
            else:
                self.set_hp(self.hp/1.6)
            return connection.on_flag_take(self)
        
        def on_grenade(self, time_left):
            if self.mode == ZOMBIE:
                self.send_chat("Zombie! You fool! You forgot to unlock the pin! It's useless now!")
                return False
            return connection.on_grenade(self, time_left)
        
        def on_hit(self, hit_amount, hit_player, type, grenade):
            new_hit = connection.on_hit(self, hit_amount, hit_player, type, grenade)
            if new_hit is not None:
                return new_hit
            other_player_location = hit_player.world_object.position
            other_player_location = (other_player_location.x, other_player_location.y, other_player_location.z)
            player_location = self.world_object.position
            player_location = (player_location.x, player_location.y, player_location.z)
            dist = floor(distance_3d(player_location, other_player_location))
            damagemulti = (sin(dist/80))+1
            new_hit = hit_amount * damagemulti
            if hit_player.mode == ZOMBIE and self.weapon == SMG_WEAPON:
                   new_hit = (new_hit/(self.protocol.ZOMBIE_HP/100))
                   if hit_player != self:
                       if new_hit >=25:
                           self.create_explosion_effect(hit_player.world_object.position)
                           self.send_chat("!!!HOLY SHIT UBER DAMAGE!!!")
            if hit_player.mode == ZOMBIE and self.weapon != SMG_WEAPON:
                   if self.weapon == SHOTGUN_WEAPON:
                       new_hit = new_hit/(self.protocol.ZOMBIE_HP/100)/8
                   else:
                       new_hit = new_hit/(self.protocol.ZOMBIE_HP/100)
                   if hit_player != self:
                       if new_hit >=25:
                           self.create_explosion_effect(hit_player.world_object.position)
                           self.send_chat("!!!HOLY SHIT UBER DAMAGE!!!")
            if self.mode == ZOMBIE and self.tool == WEAPON_TOOL:
                return False #this should never happen, but just in case
            if (self.mode == HUMAN and self.tool == SPADE_TOOL and 
                     self.team == hit_player.team and self.can_heal == True):
                   if hit_player.hp >= 100:
                       if self.health_message == True:
                           self.health_message = False
                           self.send_chat(hit_player.name + ' is at full health.')
                   elif hit_player.hp > 0:
                       self.can_heal = False
                       hit_player.set_hp(hit_player.hp + HEAL_RATE)
            return new_hit
        
        def on_kill(self, killer, type, grenade):
            if killer != None and killer != self:
                if killer.mode == HUMAN:
                    killer.refill()
                    killer.send_chat('You have been refilled!')
                else:
                    self.send_chat('THE ZOMBIES ARE COMING RAWRRR')
                    killer.set_hp(killer.hp + 25 - killer.hp/10)

            return connection.on_kill(self, killer, type, grenade)
        
        def clear_ammo(self):
            weapon_reload.player_id = self.player_id
            weapon_reload.clip_ammo = 0
            weapon_reload.reserve_ammo = 0
            self.weapon_object.clip_ammo = 0
            self.weapon_object.reserve_ammo = 0
            self.send_contained(weapon_reload)
        
        def refill(self, local = False):
            connection.refill(self, local)
            if self.mode == ZOMBIE:
                self.clear_ammo()
        
        def on_login(self, name):
            protocol = self.protocol
            self.send_chat(S_ZOMBIE_STAT % (protocol.ZOMBIE_HP, protocol.ZOMBIE_TELEPORT, protocol.ZOMBIE_SPAWN_HEIGHT))
            return connection.on_login(self, name)
    
    return ZombiesProtocol, ZombiesConnection