from collections import deque
from functools import partial
from twisted.internet.task import LoopingCall
from pyspades.world import Character
from pyspades.server import block_action, weapon_reload, position_data
from pyspades.server import input_data, weapon_input, set_tool, set_color
from pyspades.server import create_player, chat_message
from pyspades.common import make_color, Vertex3
from pyspades.constants import *
from commands import name, get_player, add, admin, alias
import commands

# TODO
# Tell enemy hits
# Persistent names and flags, detect evasion
# Water blocks

S_AHEAD_IRC = '* {admin} silently teleported ahead of {target}'
S_INSPECT = 'Began inspecting {player}'
S_INSPECT_IRC = '* {admin} began inspecting {player}'
S_UNINSPECT = 'No longer tracking {player}'
S_UNINSPECT_IRC = '* {admin} ceased tracking {player}'
S_INTROSPECTION = "Feeling introspective? Sorry, you can't inspect yourself"
S_SPY = '{player} is now spying'
S_SPY_SELF = 'You now belong to both teams'
S_NO_SPY = '{player} is no longer spying'
S_NO_SPY_SELF = "You drop the disguise"
S_HS_ENABLED = '{victim} will hit headshots normally'
S_HS_DISABLED = "{victim}'s headshots will be discarded"
S_HS_ENABLED_IRC = '* {admin} enabled headshots for {victim}'
S_HS_DISABLED_IRC = '* {admin} disabled headshots for {victim}'
S_NO_GUN = '{victim} suddenly remembers he left all of his ammo at home'
S_NO_GUN_IRC = "* {admin} vaporized {victim}'s ammo"
S_NO_GUN_SELF = "Suddenly, you're all out of bullets"
S_NO_GUN_ALL = '* {admin} incites a melee rampage by getting rid of ammo ' \
    'everywhere!'
S_LOOKING = "{player} is looking at {target}"
S_LOOKING_SELF = "{player} is looking at you"
S_CANT_SEE = "{player} is looking at {target}, but can't see there"
S_CANT_SEE_SELF = "{player} is looking at you, but can't see you"
S_GAME_PAUSED = 'Game paused'
S_GAME_UNPAUSED = 'Game unpaused'
S_PAUSED = '{player} is frozen'
S_PAUSED_IRC = '* {admin} paused {player}'
S_PAUSED_SELF = 'You were frozen in time'
S_UNPAUSED = '{player} unfrozen'
S_UNPAUSED_IRC = '* {admin} unpaused {player}'
S_UNPAUSED_SELF = 'You can move freely now'

@admin
def hacktools(connection):
    return ', '.join(['/ahead <player>', '/inspect <player>', '/nogun [player]',
        '/nogunall', '/toggleheadshot <player>', '/pause [player]', '/spy [player]'])

def destroy_block(protocol, x, y, z):
    if protocol.map.destroy_point(x, y, z):
        block_action.value = DESTROY_BLOCK
        block_action.player_id = 32
        block_action.x = x
        block_action.y = y
        block_action.z = z
        protocol.send_contained(block_action, save = True)

def xy_bfs(start_x, start_y, rule):
    open, closed = deque([(0, 0)]), []
    while open:
        xy = open.popleft()
        if xy in closed or not rule(*xy):
            continue
        closed.append(xy)
        x, y = xy
        open.append((x - 1, y))
        open.append((x + 1, y))
        open.append((x, y - 1))
        open.append((x, y + 1))
        x, y = x + start_x, y + start_y
        if x > 0 and y > 0 and x < 512 and y < 512:
            yield x, y

@admin
def ahead(connection, player):
    protocol = connection.protocol
    if connection not in protocol.players:
        raise ValueError()
    target, player = get_player(protocol, player), connection
    
    v = target.world_object.orientation.copy()
    v.z = 0.0
    v.normalize()
    v *= 32.0
    v += target.world_object.position
    v_x, v_y, v_z = (int(n) for n in v.get())
    
    lookup_radius = 10.0 ** 2
    def disc(x, y):
        d = x * x + y * y
        return d <= lookup_radius
    
    found = False
    for x, y in xy_bfs(v_x, v_y, disc):
        run = 0
        for z in xrange(v_z, 61):
            if protocol.map.get_solid(x, y, z):
                run += 1
                if run > 3:
                    found = True
                    destroy_block(protocol, x, y, z - 2)
                    destroy_block(protocol, x, y, z - 1)
                    destroy_block(protocol, x, y, z)
                    v.set(x, y, z - 2.4)
                    break
            else:
                run = 0
        if found:
            break
    player.set_location_safe(v.get())
    protocol.irc_say(S_AHEAD_IRC.format(admin = player.name,
        target = target.name))

@admin
def inspect(connection, player):
    protocol = connection.protocol
    if connection not in protocol.players:
        raise ValueError()
    target, player = get_player(protocol, player), connection
    if player is target:
        return S_INTROSPECTION
    
    if target.tracked_by is None:
        target.tracked_by = []
    target.track_looking_at = None
    if player in target.tracked_by:
        target.tracked_by.remove(player)
        irc = S_UNINSPECT_IRC.format(admin = player.name, player = target.name)
        result = S_UNINSPECT.format(player = target.name)
    else:
        target.tracked_by.append(player)
        irc = S_INSPECT_IRC.format(admin = player.name, player = target.name)
        result = S_INSPECT.format(player = target.name)
    protocol.irc_say(irc)
    return result

def fill_create_player(player, team):
    x, y, z = player.world_object.position.get()
    create_player.x = x
    create_player.y = y
    create_player.z = z
    create_player.name = player.name
    create_player.player_id = player.player_id
    create_player.weapon = player.weapon
    create_player.team = team.id

@name('spy')
@admin
def toggle_spy(connection, player = None):
    protocol = connection.protocol
    if player is not None:
        player = get_player(protocol, player)
    elif connection in protocol.players:
        player = connection
    else:
        raise ValueError()
    
    player.spy = spy = not player.spy
    player.killing = not spy
    if spy and player.invisible:
        # spy and invisibility don't get along nicely, the latter doesn't know
        # about the multiteaming when sending out create_player packets
        result = commands.invisible(connection, player.name)
        if result:
            connection.send_chat(result)
    if player.world_object and not player.world_object.dead:
        team = player.team.other if player.spy else player.team
        fill_create_player(player, team)
        protocol.send_contained(create_player, team = team, sender = player,
            save = True)
    other_message = S_SPY if spy else S_NO_SPY
    other_message = other_message.format(player = player.name)
    protocol.irc_say('* ' + other_message)
    self_message = S_SPY_SELF if spy else S_NO_SPY_SELF
    if connection is player:
        return self_message
    elif connection in protocol.players:
        player.send_chat(self_message)
        return other_message

@alias('invis')
@alias('inv')
@admin
def invisible(connection, player = None):
    protocol = connection.protocol
    if player is not None:
        player = get_player(protocol, player)
    elif connection in protocol.players:
        player = connection
    else:
        raise ValueError()
    
    if not player.invisible and player.spy:
        # disable spy before going invisible
        result = toggle_spy(connection, player.name)
        if result:
            connection.send_chat(result)
    
    commands.invisible(connection, player.name)

def reposition(player):
    # not using set_location to avoid touching the object's position
    x, y, z = player.world_object.position.get()
    if player.world_object.crouch:
        z += 1.0
    position_data.x = x
    position_data.y = y
    position_data.z = z
    player.send_contained(position_data)

@name('pause')
@admin
def toggle_pause(connection, player = None):
    protocol = connection.protocol
    if player is None:
        protocol.paused = paused = not protocol.paused
        for player in protocol.players.itervalues():
            if not player.admin:
                player.paused = paused
        if not paused:
            # immediately send orientation packets
            protocol.update_network()
        message = S_GAME_PAUSED if paused else S_GAME_UNPAUSED
        protocol.send_chat(message, irc = True)
    else:
        player = get_player(protocol, player)
        player.paused = paused = not player.paused
        irc_message = S_PAUSED_IRC if paused else S_UNPAUSED_IRC
        protocol.irc_say(irc_message.format(admin = connection.name,
            player = player.name))
        self_message = S_PAUSED_SELF if paused else S_UNPAUSED_SELF
        if connection is player:
            return self_message
        elif connection in protocol.players:
            player.send_chat(self_message)
            other_message = S_PAUSED if paused else S_UNPAUSED
            return other_message.format(player = player.name)
        

@name('toggleheadshot')
@admin
def toggle_headshot(connection, player):
    protocol = connection.protocol
    player = get_player(connection.protocol, player)
    
    player.headshots = not player.headshots
    
    message = S_HS_ENABLED_IRC if player.headshots else S_HS_DISABLED_IRC
    message = message.format(admin = connection.name, victim = player.name)
    protocol.irc_say(message)
    if connection in protocol.players:
        message = S_HS_ENABLED if player.headshots else S_HS_DISABLED
        return message.format(victim = player.name)

def empty_weapon(player):
    weapon = player.weapon_object
    weapon.set_shoot(False)
    weapon.current_ammo = 0
    weapon.current_stock = 0
    weapon_reload.player_id = player.player_id
    weapon_reload.clip_ammo = weapon.current_ammo
    weapon_reload.reserve_ammo = weapon.current_stock
    player.send_contained(weapon_reload)

@name('nogun')
@admin
def no_gun(connection, player = None):
    protocol = connection.protocol
    if player is not None:
        player = get_player(protocol, player)
    elif connection in protocol.players:
        player = connection
    else:
        raise ValueError()
    
    empty_weapon(player)
    
    message = S_NO_GUN_IRC.format(admin = connection.name, victim = player.name)
    protocol.irc_say(message)
    if connection is player:
        return S_NO_GUN_SELF
    elif connection in protocol.players:
        player.send_chat(S_NO_GUN_SELF)
        return S_NO_GUN.format(victim = player.name)

@name('nogunall')
@admin
def no_gun_all(connection):
    protocol = connection.protocol
    
    for player in protocol.players.itervalues():
        empty_weapon(player)
        player.send_chat(S_NO_GUN_SELF)
    
    message = S_NO_GUN_ALL.format(admin = connection.name)
    protocol.irc_say(message)

for func in (hacktools, ahead, inspect, no_gun, no_gun_all, toggle_spy,
    invisible, toggle_headshot, toggle_pause):
    add(func)

def pausable(func):
    def new_func(self, *arg, **kw):
        if self._paused:
            return False
        return func(self, *arg, **kw)
    return new_func

def apply_script(protocol, connection, config):
    class HackToolsConnection(connection):
        headshots = True
        tracked_by = None
        spy = False
        pause_loop = None
        _paused = False
        
        def _get_paused(self):
            return self._paused
        def _set_paused(self, value):
            if self._paused == value:
                return
            is_spectator = self.team and self.team.spectator
            if value and is_spectator:
                # spectators are unaffected
                return
            self._paused = value
            self.filter_weapon_input = value
            self.filter_animation_data = value
            self.freeze_animation = value
            send_others = partial(self.protocol.send_contained,
                sender = self, save = True)
            world_object = self.world_object
            if value:
                # start sticky position loop
                self.pause_loop = LoopingCall(reposition, self)
                self.pause_loop.start(0.08)
                self.paused_spawn = None
                self.paused_orientation = None
                if world_object is None:
                    return
                # stop walking and shooting
                world_object.set_walk(False, False, False, False)
                weapon_input.player_id = self.player_id
                weapon_input.primary = False
                weapon_input.secondary = False
                send_others(weapon_input)
            else:
                # end repositioning
                if self.pause_loop and self.pause_loop.running:
                    self.pause_loop.stop()
                self.pause_loop = None
                if self.paused_spawn:
                    # game got paused while player was waiting to spawn
                    self.paused_spawn()
                    self.paused_spawn = None
                    return
                if world_object is None:
                    return
                if self.paused_orientation:
                    # assume stored orientation
                    world_object.set_orientation(*self.paused_orientation)
                set_tool.player_id = self.player_id
                set_tool.value = self.tool
                set_color.player_id = self.player_id
                set_color.value = make_color(*self.color)
                weapon_input.player_id = self.player_id
                weapon_input.primary = world_object.primary_fire
                weapon_input.secondary = world_object.secondary_fire
                send_others(set_tool)
                send_others(set_color)
                send_others(weapon_input)
            input_data.player_id = self.player_id
            input_data.up = world_object.up
            input_data.down = world_object.down
            input_data.left = world_object.left
            input_data.right = world_object.right
            input_data.jump = world_object.jump
            input_data.crouch = world_object.crouch
            input_data.sneak = world_object.sneak
            input_data.sprint = world_object.sprint
            send_others(input_data)
        paused = property(_get_paused, _set_paused)
        
        def on_user_login(self, user_type, verbose = True):
            if user_type == 'admin':
                self.paused = False
            connection.on_user_login(self, user_type, verbose)
        
        def on_reset(self):
            # clear a queued spawn BEFORE unpausing
            self.paused_spawn = None
            self.paused = False
            connection.on_reset(self)
        
        def on_team_join(self, team):
            if self.paused and self.team is not None:
                # won't catch joining a team upon entering the game
                return False
            return connection.on_team_join(self, team)
        
        def on_login(self, name):
            if not self.team.spectator:
                for enemy in self.team.other.get_players():
                    if enemy.spy:
                        fill_create_player(enemy, self.team)
                        self.send_contained(create_player)
            connection.on_login(self, name)
        
        def on_team_changed(self, old_team):
            if self.team and not self.team.spectator:
                # maintain spy status after our team change
                for enemy in self.protocol.players.itervalues():
                    if enemy.spy:
                        fill_create_player(enemy, self.team)
                        self.send_contained(create_player)
            connection.on_team_changed(self, old_team)
        
        def spawn(self, pos = None):
            if self.paused:
                # won't catch spawning for the first time
                self.spawn_call = None
                self.paused_spawn = partial(self.spawn, pos)
                return
            if not self.spy or not self.team or self.team.spectator:
                return connection.spawn(self, pos)
            # spy: replicate ServerProtocol spawn but fork create_player packet
            self.spawn_call = None
            if pos is None:
                x, y, z = self.get_spawn_location()
                x += 0.5
                y += 0.5
                z -= 2.4
            else:
                x, y, z = pos
            returned = self.on_spawn_location((x, y, z))
            if returned is not None:
                x, y, z = returned
            if self.world_object is not None:
                self.world_object.set_position(x, y, z, True)
            else:
                self.world_object = self.protocol.world.create_object(
                    Character, Vertex3(x, y, z), None, self._on_fall)
            self.world_object.dead = False
            self.tool = WEAPON_TOOL
            self.refill(True)
            fill_create_player(self, self.team)
            if self.filter_visibility_data:
                self.send_contained(create_player)
            else:
                self.protocol.send_contained(create_player, 
                    team = self.team, save = True)
                create_player.team = self.team.other.id
                self.protocol.send_contained(create_player, 
                    team = self.team.other, save = True)
            self.on_spawn((x, y, z))
        
        def on_spawn(self, pos):
            if self.protocol.paused:
                self.paused = True
            connection.on_spawn(self, pos)
        
        def on_disconnect(self):
            self.tracked_by = None
            self.track_looking_at = None
            for player in self.protocol.players.itervalues():
                if player.tracked_by and self in player.tracked_by:
                    player.tracked_by.remove(self)
            connection.on_disconnect(self)
        
        def on_chat_sent(self, value, global_message):
            if not global_message:
                chat_message.player_id = self.player_id
                chat_message.chat_type = CHAT_TEAM
                chat_message.value = value
                if self.spy and not self.team.spectator:
                    # make sure a spy's message gets to both teams
                    for enemy in self.team.other.get_players():
                        if not enemy.spy:
                            enemy.send_contained(chat_message)
                # send spies a carbon copy of the message
                for player in self.protocol.players.itervalues():
                    if (player.spy and player is not self and 
                        (player.team.spectator or self.team is not player.team)):
                        player.send_contained(chat_message)
            connection.on_chat_sent(self, value, global_message)
        
        @pausable
        def on_grenade(self, time_left):
            return connection.on_grenade(self, time_left)
        
        @pausable
        def on_weapon_set(self, value):
            return connection.on_weapon_set(self, value)
        
        @pausable
        def on_block_build_attempt(self, x, y, z):
            return connection.on_block_build_attempt(self, x, y, z)
        
        @pausable
        def on_line_build_attempt(self, points):
            return connection.on_line_build_attempt(self, points)
        
        @pausable
        def on_block_destroy(self, x, y, z, mode):
            return connection.on_block_destroy(self, x, y, z, mode)
        
        @pausable
        def on_flag_take(self):
            if self.spy:
                return False
            return connection.on_flag_take(self)
        
        @pausable
        def on_hit(self, hit_amount, hit_player, type, grenade):
            if not self.headshots and type == HEADSHOT_KILL:
                return False
            return connection.on_hit(self, hit_amount, hit_player, type, grenade)
        
        def hit(self, value, by = None, type = WEAPON_KILL):
            friendly_fire = self.protocol.friendly_fire
            if by is not None and self.spy and friendly_fire != False:
                return
            connection.hit(self, value, by, type)
        
        def on_kill(self, killer, type, grenade):
            if self.pause_loop and self.pause_loop.running:
                self.pause_loop.stop()
            return connection.on_kill(self, killer, type, grenade)
        
        def on_orientation_update(self, x, y, z):
            if self.paused:
                self.paused_orientation = (x, y, z)
                return False
            if self.tracked_by:
                # see if we're peering in our trackers' direction
                looking_at, closest = None, None
                obj = self.world_object
                ori = obj.orientation
                for player in self.tracked_by:
                    if player.world_object is None:
                        continue
                    delta = player.world_object.position - obj.position
                    if delta.is_zero():
                        continue
                    distance = delta.length()
                    theta = ori.x * delta.x + ori.y * delta.y + ori.z * delta.z
                    theta /= distance
                    if theta >= 0.988:
                        if looking_at is None or distance < closest:
                            looking_at, closest = player, distance
                if looking_at and looking_at is not self.track_looking_at:
                    # warn pertinent players
                    can_see = obj.can_see(*looking_at.get_location())
                    message = S_LOOKING if can_see else S_CANT_SEE
                    message = message.format(player = self.name,
                        target = looking_at.name)
                    for player in self.tracked_by:
                        if player is not looking_at:
                            player.send_chat(message)
                    message = S_LOOKING_SELF if can_see else S_CANT_SEE_SELF
                    looking_at.send_chat(message.format(player = self.name))
                self.track_looking_at = looking_at
            return connection.on_orientation_update(self, x, y, z)
    
    class HackToolsProtocol(protocol):
        paused = False
        
        def on_map_leave(self):
            self.paused = False
            protocol.on_map_leave(self)
    
    return HackToolsProtocol, HackToolsConnection