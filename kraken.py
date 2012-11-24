from collections import deque
from math import cos, sin, sqrt, ceil, pi
from random import randrange, uniform, choice
from operator import itemgetter, attrgetter
from itertools import product

from twisted.internet import reactor
from twisted.internet.task import LoopingCall
from pyspades.server import Territory
from pyspades.server import orientation_data, move_object, grenade_packet
from pyspades.server import block_action, set_color, position_data
from pyspades.world import Grenade
from pyspades.common import Vertex3, Quaternion, make_color, coordinates
from pyspades.collision import vector_collision, distance_3d_vector
from pyspades.constants import *
from commands import name, add, get_player, admin

ALLOW_KRAKEN_COMMAND = True

USE_DAYCYCLE = False
RESPAWN_TIME = 15
FALLING_BLOCK_COLOR = (0x60, 0x60, 0x60)
FALLING_BLOCK_DAMAGE = 100
FALLING_BLOCK_Z = 0
REGEN_ONSET = 2.0
REGEN_FREQUENCY = 0.15
REGEN_AMOUNT = 3
GRAB_DAMAGE = 40
EYE_PAIN_TIME = 8.0
KRAKEN_BLACK = (0,0,0)
KRAKEN_BLOOD = (120, 255, 120)
KRAKEN_EYE_SMALL = [
    ( 0, 0, -1, (0xC0, 0x00, 0x00)),
    ( 0, 0, -2, (0x40, 0x00, 0x00)),
    ( 0, 0, -3, (0xC0, 0x00, 0x00)),
    (-1, 0, -1, (0xFF, 0x00, 0x00)),
    (-1, 0, -2, (0xC0, 0x00, 0x00)),
    (-1, 0, -3, (0x80, 0x00, 0x00)),
    ( 1, 0, -1, (0xFF, 0x00, 0x00)),
    ( 1, 0, -2, (0xC0, 0x00, 0x00)),
    ( 1, 0, -3, (0xFF, 0xFF, 0xFF))]
KRAKEN_EYE_SMALL_CLOSED = [
    (-1, 0, -1, (0x00, 0x00, 0x00)),
    (-1, 0, -2, (0x00, 0x00, 0x00)),
    (-1, 0, -3, (0x00, 0x00, 0x00)),
    ( 1, 0, -1, (0x00, 0x00, 0x00)),
    ( 1, 0, -2, (0x00, 0x00, 0x00)),
    ( 1, 0, -3, (0x00, 0x00, 0x00)),
    ( 0, 0, -1, (0x00, 0x00, 0x00)),
    ( 0, 0, -2, (0x00, 0x00, 0x00)),
    ( 0, 0, -3, (0x00, 0x00, 0x00))]

def cube(s):
    s0, s1 = -s / 2 + 1, s / 2 + 1
    return product(xrange(s0, s1), repeat = 3)

def prism(x, y, z, w, d, h):
    return product(xrange(x, x + w), xrange(y, y + d), xrange(z, z + h))

def plane(r):
    r0, r1 = -r / 2 + 1, r / 2 + 1
    return product(xrange(r0, r1), repeat = 2)

def disc(rr, x = 0, y = 0, min_rr = None):
    for u, v in plane(rr):
        d = u * u + v * v
        if d > rr or (min_rr and d < min_rr):
            continue
        yield x + u, y + v

def sphere(r, x = 0, y = 0, z = 0, min_r = None):
    rr = r * r
    min_rr = min_r and min_r * min_r
    for w, v, u in cube(r):
        d = u * u + v * v + w * w
        if d > rr or (min_r and d < min_rr):
            continue
        yield x + u, y + v, z + w

def aabb(x, y, z, i, j, k, w, d, h):
    return not (x < i or x > i + w or y < j or y > j + d or z < k or z > k + h)

def aabb_centered(x, y, z, i, j, k, s):
    return not (x < i - s or x > i + s or y < j - s or y > j + s or
        z < k - s or z > k + s)

def randrangerect(x1, y1, x2, y2):
    return randrange(x1, x2), randrange(y1, y2)

def fall_eta(height):
    return 2.0 * (height / 64.0) ** 0.75

def is_valid_enemy(player):
    return not (player.world_object is None or player.world_object.dead or
        player.grabbed_by or player.trapped or player.regenerating or player.god)

class Animated:
    blocks_per_cycle = 3
    build_interval = 0.01
    build_queue = None
    build_loop = None
    blocks = None
    
    def __init__(self, protocol):
        self.protocol = protocol
        self.build_queue = deque()
        self.build_loop = LoopingCall(self.build_cycle)
        self.build_loop.start(self.build_interval)
        self.blocks = set()
    
    def build_cycle(self):
        if not self.build_queue:
            return        
        blocks_left = self.blocks_per_cycle
        last_color = None
        while self.build_queue and blocks_left > 0:
            x, y, z, color = self.build_queue.popleft()
            if color != last_color:
                self.protocol.set_block_color(color)
                last_color = color
            if self.protocol.build_block(x, y, z, color):
                blocks_left -= 1

class Tentacle(Animated):
    dead = False
    dying = False
    on_death = None
    on_removed = None
    parent = None
    protocol = None
    origin = None
    up = None
    orientation = None
    start_orientation = None
    target_orientation = None
    lerp_t = None
    facing = None
    sections = None
    radius = 2
    spread = radius / 2.0
    follow = None
    follow_interval = 1.3
    follow_timer = follow_interval
    initial_growth_interval = 0.2
    growth_interval = initial_growth_interval
    growth_timer = growth_interval
    blocks_destroyed = None
    last_block_destroyed = None
    growing = True
    withdraw = False
    grabbed_player = None
    max_hp = None
    
    def __init__(self, protocol, parent, (x, y, z)):
        Animated.__init__(self, protocol)
        self.parent = parent
        self.origin = Vertex3(x, y, z)
        self.up = Vertex3(0.0, 0.0, -1.0)
        self.orientation = Quaternion()
        self.facing = self.orientation.transform_vector(self.up)
        self.sections = []
        self.blocks_destroyed = []
        self.parent.tentacles.append(self)
        self.find_target()
    
    def find_target(self):
        best = None
        best_dist = None
        best_followed = None
        for player in self.protocol.players.values():
            if not is_valid_enemy(player):
                continue
            dist = distance_3d_vector(player.world_object.position, self.origin)
            followed = self.parent.is_enemy_targeted(player)
            if not best or dist < best_dist or best_followed and not followed:
                best, best_dist, best_followed = player, dist, followed
        self.follow = best
    
    def think(self, dt):
        tip = self.sections and self.sections[-1][0] or self.origin
        
        self.follow_timer -= dt
        if self.follow and not is_valid_enemy(self.follow):
            self.find_target()
            if not self.follow:
                self.growth_timer = 0.66
                self.growing = False
                self.withdraw = True
        elif self.follow and self.follow_timer <= 0.0:
            self.follow_timer = self.follow_interval
            follow_pos = self.follow.world_object.position
            direction = follow_pos - tip
            q = self.facing.get_rotation_to(direction)
            self.start_orientation = Quaternion(*self.orientation.get())
            self.target_orientation = q * self.orientation
            self.lerp_t = 0.0
        if self.target_orientation and self.lerp_t <= 1.0:
            self.orientation = self.start_orientation.slerp(
                self.target_orientation, self.lerp_t)
            self.lerp_t += 0.02
        self.facing = self.orientation.transform_vector(self.up)
        self.facing.normalize()
        
        self.growth_timer -= dt
        if self.growth_timer <= 0.0:
            self.growth_timer = self.growth_interval
            if self.growing and self.follow:
                tip = self.grow(tip.copy())
            elif self.withdraw:
                if self.sections:
                    pos, blocks = self.sections.pop()
                    tip = pos
                    for uvw in blocks:
                        if not self.parent.is_location_inside(uvw, skip = self):
                            self.protocol.remove_block(*uvw)
                        self.blocks.discard(uvw)
                else:
                    for uvw in self.blocks:
                        if not self.parent.is_location_inside(uvw, skip = self):
                            self.protocol.remove_block(*uvw)
                    self.dead = True
                    if self.on_removed:
                        self.on_removed(self)
        
        player = self.grabbed_player
        if player:
            if self.dead or not player.world_object or player.world_object.dead:
                player.grabbed_by = None
                self.grabbed_player = None
            else:
                player.set_location((tip.x, tip.y, tip.z - 1.0))
                if tip.z >= 63:
                    player.got_water_damage = True
                    player.kill(type = FALL_KILL)
                    player.got_water_damage = False
    
    def on_block_destroy(self, x, y, z, mode):
        if mode == SPADE_DESTROY and (x, y, z) in self.blocks:
            return False
    
    def on_block_removed(self, x, y, z):
        xyz = (x, y, z)
        if xyz not in self.blocks:
            return
        self.blocks.discard(xyz)
        total_damage = 0.0
        for u, v, w in self.blocks_destroyed:
            xu, yv, zw = x - u, y - v, z - w
            d = sqrt(xu*xu + yv*yv + zw*zw)
            total_damage += d >= 1.0 and 1.0 / d or 1.0
            if total_damage > self.max_hp:
                self.fracture(x, y, z)
                self.last_block_destroyed = None
                self.die()
                if self.on_death:
                    self.on_death(self)
                return
        if self.last_block_destroyed:
            self.protocol.set_block_color(KRAKEN_BLOOD)
            u, v, w = self.last_block_destroyed
            self.protocol.build_block(u, v, w, KRAKEN_BLOOD)
            self.blocks.add(self.last_block_destroyed)
        self.last_block_destroyed = xyz
        self.blocks_destroyed.append(xyz)
    
    def die(self):
        self.follow = None
        self.target_orientation = None
        if self.grabbed_player:
            self.grabbed_player.grabbed_by = None
        self.grabbed_player = None
        self.growth_timer = 0.66
        speedup = 2.0 + max(len(self.sections) / 140.0, 1.0)
        self.growth_interval = self.initial_growth_interval / speedup
        self.growing = False
        self.withdraw = True
        self.dying = True
    
    def fracture(self, x, y, z):
        protocol = self.protocol
        radius = self.radius
        for uvw in sphere(int(radius * 1.5), x, y, z):
            if not self.parent.is_location_inside(uvw, skip = self):
                protocol.remove_block(*uvw)
            self.blocks.discard(uvw)
        to_remove = []
        breakpoint = False
        while self.sections:
            pos, blocks = self.sections.pop()
            for uvw in blocks:
                if not self.parent.is_location_inside(uvw, skip = self):
                    if breakpoint:
                        protocol.remove_block(*uvw)
                    else:
                        to_remove.append(uvw)
                self.blocks.discard(uvw)
            if breakpoint:
                break
            i, j, k = pos.get()
            breakpoint = aabb_centered(x, y, z, i, j, k, radius)
        if self.sections:
            self.sections.pop()
        for u, v, w in to_remove:
            protocol.remove_block(u, v, w)
    
    def grow(self, tip):
        if self.sections:
            tip += self.facing * self.spread
        map = self.protocol.map
        radius = self.radius
        ix, iy, iz = int(tip.x), int(tip.y), int(tip.z)
        blocks = []
        destroyed = 0
        for x, y, z in sphere(radius, ix, iy, iz):
            if (x < 0 or x >= 512 or y < 0 or y >= 512 or 
                z < 0 or z >= 63):
                continue
            xyz = (x, y, z)
            if xyz not in self.blocks:
                if not map.get_solid(x, y, z):
                    blocks.append(xyz)
                    self.blocks.add(xyz)
                    self.build_queue.append(xyz + (KRAKEN_BLACK,))
                elif not self.parent.is_location_inside(xyz, skip = self):
                    destroyed += 1
        if destroyed >= radius:
            for x, y, z in sphere(radius + 2, ix, iy, iz, min_r = radius):
                if self.parent.is_location_inside((x, y, z)):
                    continue
                self.protocol.remove_block(x, y, z)
            self.protocol.create_explosion_effect(tip)
        for player in self.protocol.players.values():
            if not is_valid_enemy(player):
                continue
            pos = player.world_object.position
            if vector_collision(pos, tip, radius * 0.75):
                self.follow = None
                self.target_orientation = None
                self.growth_timer = 0.4
                self.growing = False
                self.withdraw = True
                self.grabbed_player = player
                player.grabbed_by = self
                player.set_location((tip.x, tip.y, tip.z - 1.0))
                player.hit(GRAB_DAMAGE)
                break
        self.sections.append((tip, blocks))
        return tip

class Eye():
    parent = None
    protocol = None
    dead = False
    blocks = None
    origin_x = None
    pos = None
    base = None
    hits = None
    look_interval_min = 0.8
    look_interval_max = 2.5
    look_timer = look_interval_max
    on_hit = None
    create_call = None
    
    def __init__(self, parent, base, ox, oy, oz, hits = 3):
        self.parent = parent
        self.protocol = parent.protocol
        self.blocks = set()
        self.pos = parent.origin.copy().translate(ox, oy, oz)
        self.origin_x = self.pos.x
        self.base = base[:]
        self.hits = hits
        parent.eyes.append(self)
    
    def think(self, dt):
        if not self.blocks:
            return
        self.look_timer -= dt
        if self.look_timer <= 0.0:
            self.look_timer = uniform(self.look_interval_min,
                self.look_interval_max)
            old_x = self.pos.x
            self.pos.x = max(self.origin_x - 1, min(self.origin_x + 1,
                self.pos.x + choice([-1, 1])))
            if old_x != self.pos.x:
                old_blocks = self.blocks
                self.blocks = set()
                self.create_instant()
                old_blocks -= self.blocks
                self.protocol.set_block_color(KRAKEN_BLACK)
                for x, y, z in old_blocks:
                    self.protocol.build_block(x, y, z, KRAKEN_BLACK, 
                        force = True)
    
    def create(self, block_queue = None, close = False):
        if block_queue is None:
            block_queue = deque(self.base)
        last_color = None
        x, y, z = self.pos.get()
        x_d = None
        while block_queue:
            u, v, w, color = block_queue[0]
            if x_d is None:
                x_d = abs(u)
            elif abs(u) != x_d:
                break
            if color != last_color:
                self.protocol.set_block_color(color)
                last_color = color
            u, v, w = x + u, y + v, z + w
            uvw = (u, v, w)
            self.protocol.build_block(u, v, w, color, force = True)
            if not close:
                self.parent.head.discard(uvw)
                self.blocks.add(uvw)
            block_queue.popleft()
        if block_queue:
            self.create_call = reactor.callLater(0.25, self.create, block_queue)
    
    def create_instant(self, block_list = None):
        if block_list is None:
            block_list = self.base
        last_color = None
        x, y, z = self.pos.get()
        block_list = sorted(block_list, key = itemgetter(3))
        for u, v, w, color in block_list:
            if color != last_color:
                self.protocol.set_block_color(color)
                last_color = color
            u, v, w = x + u, y + v, z + w
            uvw = (u, v, w)
            self.protocol.build_block(u, v, w, color, force = True)
            self.parent.head.discard(uvw)
            self.blocks.add(uvw)
    
    def on_block_removed(self, x, y, z):
        xyz = (x, y, z)
        if self.dead or xyz not in self.blocks:
            return
        protocol = self.protocol
        protocol.create_explosion_effect(Vertex3(x, y, z))
        self.parent.build_queue.append((x, y, z, KRAKEN_BLOOD))
        self.hits -= 1
        if self.hits > 0:
            self.pain()
            uvw = (x - self.pos.x, y - self.pos.y, z - self.pos.z)
            i = [uvwc[:-1] for uvwc in self.base].index(uvw)
            self.base[i] = uvw + (KRAKEN_BLOOD,)
        else:
            self.close()
            self.dead = True
        if self.on_hit:
            self.on_hit(self)
    
    def close(self):
        self.parent.head.update(self.blocks)
        self.blocks.clear()
        if self.create_call and self.create_call.active():
            self.create_call.cancel()
        reactor.callLater(0.5, self.create, deque(KRAKEN_EYE_SMALL_CLOSED),
            close = True)
    
    def pain(self):
        self.close()
        reactor.callLater(EYE_PAIN_TIME, self.create)
        self.look_timer = EYE_PAIN_TIME + self.look_interval_min

class Kraken(Animated):
    dead = False
    origin = None
    tentacles = None
    head = None
    eyes = None
    max_hp = 10.0
    hp = max_hp
    size = 7
    on_last_tentacle_death = None
    on_death = None
    on_removed = None
    finally_call = None
    phase = 0
    
    def __init__(self, protocol, (x, y, z)):
        Animated.__init__(self, protocol)
        self.origin = Vertex3(x, y, z)
        self.head = set()
        self.eyes = []
        self.tentacles = []
    
    def is_location_inside(self, location, skip = None):
        if location in self.head:
            return True
        for eye in self.eyes:
            if location in eye.blocks:
                return True
        for t in self.tentacles:
            if t is not skip and location in t.blocks:
                return True
        return False
    
    def is_enemy_targeted(self, player):
        for t in self.tentacles:
            if t.follow is player:
                return True
        return False
    
    def on_block_destroy(self, x, y, z, mode):
        for t in self.tentacles:
            if t.on_block_destroy(x, y, z, mode) == False:
                return False
    
    def on_block_removed(self, x, y, z):
        eye_died = False
        for eye in self.eyes:
            eye.on_block_removed(x, y, z)
            eye_died = eye_died or eye.dead
        if eye_died:
            self.eyes = [eye for eye in self.eyes if not eye.dead]
            if not self.eyes:
                self.die()
        
        for t in self.tentacles:
            t.on_block_removed(x, y, z)
    
    def die(self):
        protocol = self.protocol
        def remove(this, remover, blocks):
            if blocks:
                remover(*blocks.pop())
                reactor.callLater(0.01, this, this, remover, blocks)
            elif self.on_removed:
                self.on_removed(self)
        def explode(this, effect, blocks, left):
            x = self.origin.x + uniform(-5.0, 5.0)
            y = self.origin.y + self.size + 1.0
            z = self.origin.z + uniform(-15.0, 0.0)
            effect(Vertex3(x, y, z))
            if not blocks or left <= 0:
                return
            delay = uniform(0.3, 0.8)
            left -= 1
            reactor.callLater(delay, this, this, effect, blocks, left)
        remove(remove, protocol.remove_block, self.head)
        explode(explode, protocol.create_explosion_effect, self.head, 10)
        
        self.dead = True
        for t in self.tentacles:
            t.die()        
        if self.on_death:
            self.on_death(self)
    
    def think(self, dt):
        for eye in self.eyes:
            eye.think(dt)
        
        rebuild_list = False
        for t in self.tentacles:
            t.think(dt)
            rebuild_list = rebuild_list or t.dead
        if rebuild_list:
            self.tentacles = [t for t in self.tentacles if not t.dead]
            if not self.tentacles and self.on_last_tentacle_death:
                self.on_last_tentacle_death(self)
    
    def hit(self, value, rate):
        hp_bar = self.protocol.hp_bar
        if not hp_bar.shown:
            hp_bar.progress = 1.0 - self.hp / self.max_hp
            hp_bar.show()
        self.hp = max(self.hp - value, 0)
        previous_rate = hp_bar.rate
        hp_bar.get_progress(True)
        hp_bar.rate = rate
        hp_bar.update_rate()
        hp_bar.send_progress()
        target_progress = 1.0 - self.hp / self.max_hp
        delay = (target_progress - hp_bar.progress) / hp_bar.rate_value
        hp_call = hp_bar.hp_call
        if hp_call and hp_call.active():
            if previous_rate == 0:
                hp_call.cancel()
            else:
                hp_call.reset(delay)
                return
        hp_bar.hp_call = reactor.callLater(delay, hp_bar.stop)
    
    def create_head(self, head_list, height = None):
        height = height or len(head_list)
        x, y, z = self.origin.get()
        for d in head_list[-height:]:
            for u, v in d:
                xyzc = (x + u, y + v, z, KRAKEN_BLACK)
                self.build_queue.append(xyzc)
                self.head.add(xyzc[:-1])
            z -= 1
        if height < len(head_list):
            delay = 0.6
            reactor.callLater(delay, self.create_head, head_list, height + 6)

force_boss = False

@admin
def kraken(connection, value = None):
    global force_boss
    protocol = connection.protocol
    if protocol.game_mode != TC_MODE:
        return 'Unfortunately, the game mode is required to be TC. Change it then restart'
    if not protocol.boss_ready:
        force_boss = True
        return 'The next map will be kraken-ready. Change maps then try again'
    if protocol.boss:
        return "There is already a kraken! Why can't I hold all these krakens?"
    try:
        x, y = coordinates(value)
    except (ValueError):
        return 'Need coordinates where to spawn the kraken, e.g /kraken E3'
    start_kraken(protocol, max(x, 64), max(y, 64))

if ALLOW_KRAKEN_COMMAND:
    add(kraken)

def start_kraken(protocol, x, y, hardcore = False, finally_call = None):
    y += 32
    boss = Kraken(protocol, (x, y - 12, 63))
    protocol.boss = boss
    if USE_DAYCYCLE and protocol.daycycle_loop.running:
        protocol.daycycle_loop.stop()
    
    arena = getattr(protocol.map_info.info, 'arena', None)
    if arena:
        arena_center = (int((arena[2] - arena[0]) / 2.0 + arena[0]),
            int((arena[3] - arena[1]) / 2.0 + arena[1]))
        arena_radius = min(arena[2] - arena[0], arena[3] - arena[1]) / 2.0
    
    def randring():
        min_r, max_r = 12.0, 32.0
        r = uniform(min_r, max_r)
        a = uniform(0.0, pi)
        return x + cos(a) * r, y + sin(a) * r, 63
    
    def randring_arena():
        if not arena:
            return randring()
        r = uniform(arena_radius, arena_radius * 1.2)
        a = uniform(0.0, 2*pi)
        x, y = arena_center
        return x + cos(a) * r, y + sin(a) * r, 63
    
    def minor_hit(caller = None):
        boss.hit(1.0, 1)
        caller.on_removed = None
    
    def major_hit(caller = None):
        boss.hit(3.0, 1)
    
    def major_hit_and_progress(caller = None):
        caller.on_hit = major_hit
        major_hit()
        progress()
    
    def major_hit_and_pain(caller = None):
        major_hit()
        boss_alive = False
        for eye in caller.parent.eyes:
            if eye is not caller and not eye.dead:
                eye.pain()
                boss_alive = True
        if boss_alive and caller.dead:
            falling_blocks_start()
    
    def respawn_tentacle(caller = None):
        if boss and not boss.dead:
            reactor.callLater(5.0, spawn_tentacles, 1, True)
    
    def spawn_tentacles(amount, respawn = False, fast = False, arena = False,
        no_hit = False):
        if not hardcore:
            toughness = max(3.0, min(10.0, len(protocol.players) * 0.5))
        else:
            toughness = max(5.0, min(13.0, len(protocol.players) * 0.85))
        if boss and not boss.dead:
            for i in xrange(amount):
                origin = randring_arena() if arena else randring()
                t = Tentacle(protocol, boss, origin)
                t.max_hp = toughness
                t.growth_timer = uniform(i * 1.0, i * 1.2)
                if hardcore:
                    t.initial_growth_interval *= 0.8
                if fast:
                    t.initial_growth_interval *= 0.5
                else:
                    t.follow_timer = 2.0
                t.growth_interval = t.initial_growth_interval
                if respawn:
                    t.on_removed = respawn_tentacle
                elif not no_hit:
                    t.on_death = minor_hit
                    t.on_removed = minor_hit
    
    def falling_blocks_cycle():
        alive_players = filter(is_valid_enemy, protocol.players.values())
        if not alive_players:
            return
        player = choice(alive_players)
        x, y, z = player.world_object.position.get()
        protocol.create_falling_block(int(x), int(y), randrange(2, 4), 2)
    
    def falling_blocks_start():
        for i in range(20):
            reactor.callLater(i * 0.4, falling_blocks_cycle)
    
    def squid_head():
        h = []
        for i in xrange(37, 5, -2):
            h.append(list(disc(i, min_rr = i - 15)))
        return h
    
    def squid_head_large():
        h = []
        for i in xrange(42, 3, -2):
            ii = int(i ** 1.3)
            h.append(list(disc(ii, y = int(sqrt(i)), min_rr = i + 10)))
        return h
    
    def regenerate_players():
        for player in protocol.players.values():
            player.trapped = False
            player.last_hit = reactor.seconds()
            player.regenerating = True
            if not player.world_object.dead:
                player.regen_loop.start(REGEN_FREQUENCY)
            else:
                player.spawn(player.world_object.position.get())
    
    def round_end(caller = None):
        regenerate_players()
        reactor.callLater(8.0, progress)
    
    def round_end_delay(caller = None):
        reactor.callLater(10.0, round_end)
    
    def round_start(caller = None):
        for player in protocol.players.values():
            player.regenerating = False
    
    def progress_delay(caller = None):
        reactor.callLater(6.0, progress)
    
    def victory(caller = None):
        regenerate_players()
        if USE_DAYCYCLE:
            protocol.current_time = 23.30
            protocol.update_day_color()
    
    def cleanup(caller = None):
        round_start()
        protocol.boss = None
        if USE_DAYCYCLE and protocol.daycycle_loop.running:
            protocol.daycycle_loop.stop()
        if caller.finally_call:
            caller.finally_call(caller)
    
    def red_sky():
        if USE_DAYCYCLE:
            protocol.day_colors = [
                ( 0.00, (0.5527, 0.24, 0.94), False),
                ( 0.10, (0.0,    0.05, 0.05), True),
                ( 0.20, (0.0,    1.00, 0.34), False),
                (23.30, (0.0,    1.00, 0.34), False),
                (23.50, (0.5527, 0.24, 0.94), False)]
            protocol.current_time = 0.00
            protocol.target_color_index = 0
            protocol.update_day_color()
            if not protocol.daycycle_loop.running:
                protocol.daycycle_loop.start(protocol.day_update_frequency)
    
    progress = None
    
    def progress_normal(caller = None):
        boss.phase += 1
        round_start()
        
        if boss.phase == 1:
            boss.on_last_tentacle_death = progress_delay
            spawn_tentacles(2)
        elif boss.phase == 2:
            boss.on_last_tentacle_death = round_end
            spawn_tentacles(4)
        elif boss.phase == 3:
            boss.on_last_tentacle_death = round_end
            spawn_tentacles(3, fast = True)
        elif boss.phase == 4:
            boss.on_last_tentacle_death = None
            boss.on_death = round_end_delay
            boss.size = 7
            boss.create_head(squid_head())
            eye = Eye(boss, KRAKEN_EYE_SMALL, 0, 5, -1, hits = 5)
            eye.on_hit = major_hit_and_progress
            reactor.callLater(7.0, eye.create)
        elif boss.phase == 5:
            spawn_tentacles(3, respawn = True)
            spawn_tentacles(2, arena = True, no_hit = True)
        elif boss.phase == 6:
            protocol.send_chat('LOOK UP!', global_message = None)
            falling_blocks_start()
            reactor.callLater(15.0, round_end)
        elif boss.phase == 7:
            boss.dead = False
            boss.on_last_tentacle_death = round_end
            spawn_tentacles(4, fast = True, arena = True)
        elif boss.phase == 8:
            red_sky()
            boss.on_last_tentacle_death = None
            boss.on_death = victory
            boss.on_removed = cleanup
            boss.finally_call = finally_call
            boss.origin.y -= 24
            boss.size = 16
            boss.create_head(squid_head_large())
            eye = Eye(boss, KRAKEN_EYE_SMALL, 0, 16, -2, hits = 4)
            eye.on_hit = major_hit_and_pain
            reactor.callLater(16.0, eye.create)
            eye = Eye(boss, KRAKEN_EYE_SMALL, 0, 14, -6, hits = 4)
            eye.on_hit = major_hit_and_pain
            reactor.callLater(16.0, eye.create)
            reactor.callLater(18.0, spawn_tentacles, 5, respawn = True)
    
    def progress_hardcore(caller = None):
        boss.phase += 1
        round_start()
        
        if boss.phase == 1:
            boss.on_last_tentacle_death = progress_delay
            spawn_tentacles(3)
            falling_blocks_start()
        elif boss.phase == 2:
            boss.on_last_tentacle_death = round_end
            spawn_tentacles(4, fast = True)
        elif boss.phase == 3:
            boss.on_last_tentacle_death = None
            boss.on_death = round_end_delay
            boss.size = 7
            boss.create_head(squid_head())
            eye = Eye(boss, KRAKEN_EYE_SMALL, 0, 5, -1, hits = 8)
            eye.look_interval_min *= 0.8
            eye.look_interval_max *= 0.6
            eye.on_hit = major_hit_and_progress
            reactor.callLater(7.0, eye.create)
        elif boss.phase == 4:
            spawn_tentacles(3, respawn = True)
            spawn_tentacles(3, arena = True, no_hit = True)
        elif boss.phase == 5:
            boss.dead = False
            boss.on_last_tentacle_death = round_end
            spawn_tentacles(5, fast = True, arena = True)
        elif boss.phase == 6:
            red_sky()
            boss.on_last_tentacle_death = None
            boss.on_death = victory
            boss.on_removed = cleanup
            boss.finally_call = finally_call
            boss.origin.y -= 24
            boss.size = 16
            boss.create_head(squid_head_large())
            eye = Eye(boss, KRAKEN_EYE_SMALL, 0, 16, -2, hits = 6)
            eye.look_interval_min *= 0.8
            eye.look_interval_max *= 0.6
            eye.on_hit = major_hit_and_pain
            reactor.callLater(16.0, eye.create)
            eye = Eye(boss, KRAKEN_EYE_SMALL, 0, 14, -6, hits = 6)
            eye.look_interval_min *= 0.8
            eye.look_interval_max *= 0.6
            eye.on_hit = major_hit_and_pain
            reactor.callLater(16.0, eye.create)
            reactor.callLater(18.0, spawn_tentacles, 5, respawn = True)
            reactor.callLater(14.0, falling_blocks_start)
    
    boss.blocks_per_cycle = 2
    boss.build_interval = 0.01
    if not hardcore:
        progress = progress_normal
        boss.hp = boss.max_hp = 2.0 + 4.0 + 3.0 + 5*3.0 + 4.0 + (4 + 4)*3.0
    else:
        progress = progress_hardcore
        boss.hp = boss.max_hp = 3.0 + 4.0 + 8*3.0 + 5.0 + (6 + 6)*3.0
    progress()
    return boss

class BossTerritory(Territory):
    shown = False
    hp_call = None
    
    def add_player(self, player):
        return
    
    def remove_player(self, player):
        return
    
    def update_rate(self):
        self.rate_value = self.rate * TC_CAPTURE_RATE
        self.capturing_team = (self.rate_value < 0 and
            self.protocol.blue_team or self.protocol.green_team)
        self.start = reactor.seconds()
    
    def show(self):
        self.shown = True
        for player in self.protocol.players.values():
            self.update_for_player(player)
    
    def hide(self):
        self.shown = False
        self.update()
    
    def stop(self):
        self.rate = 0
        self.get_progress(True)
        self.update_rate()
        self.send_progress()
        self.hp_call = reactor.callLater(3.0, self.hide)
    
    def update_for_player(self, connection, orientation = None):
        x, y, z = orientation or connection.world_object.orientation.get()
        v = Vertex3(x, y, 0.0)
        v.normalize()
        v *= -10.0
        v += connection.world_object.position
        move_object.object_type = self.id
        move_object.state = self.team and self.team.id or NEUTRAL_TEAM
        move_object.x = v.x
        move_object.y = v.y
        move_object.z = v.z
        connection.send_contained(move_object)

def apply_script(protocol, connection, config):
    class BossProtocol(protocol):
        game_mode = TC_MODE
        
        boss = None
        boss_ready = False
        hp_bar = None
        
        def start_kraken(self, x, y, hardcore = False, finally_call = None):
            return start_kraken(self, x, y, hardcore, finally_call)
        
        def is_indestructable(self, x, y, z):
            if self.boss:
                if self.boss.head and (x, y, z) in self.boss.head:
                    return True
            return protocol.is_indestructable(self, x, y, z)
        
        def on_world_update(self):
            if self.boss:
                self.boss.think(UPDATE_FREQUENCY)
            protocol.on_world_update(self)
        
        def on_map_change(self, map):
            self.boss = None
            self.boss_ready = False
            self.hp_bar = None
            protocol.on_map_change(self, map)
        
        def get_cp_entities(self):
            global force_boss
            if force_boss or getattr(self.map_info.info, 'boss', False):
                if (USE_DAYCYCLE and self.daycycle_loop and
                    self.daycycle_loop.running):
                    self.daycycle_loop.stop()
                force_boss = False
                self.boss_ready = True
                self.hp_bar = BossTerritory(0, self, 0.0, 0.0, 0.0)
                self.hp_bar.team = self.green_team
                return [self.hp_bar]
            return protocol.get_cp_entities(self)
        
        def create_explosion_effect(self, position):
            self.world.create_object(Grenade, 0.0, position, None, 
                Vertex3(), None)
            grenade_packet.value = 0.0
            grenade_packet.player_id = 32
            grenade_packet.position = position.get()
            grenade_packet.velocity = (0.0, 0.0, 0.0)
            self.send_contained(grenade_packet)
        
        def falling_block_collide(self, x, y, z, size):
            if not self.map.get_solid(x, y, z):
                new_z = self.map.get_z(x, y)
                if new_z > z:
                    remaining = fall_eta(new_z - z)
                    reactor.callLater(remaining, self.falling_block_collide,
                        x, y, new_z, size)
                    return
            for player in self.players.values():
                i, j, k = player.world_object.position.get()
                s = size + 3.0
                if aabb(i, j, k, x - 1.5, y - 1.5, z - 5.0, s, s, 6.0):
                    player.hit(FALLING_BLOCK_DAMAGE, type = FALL_KILL)
            half_size = int(ceil(size / 2.0))
            ox, oy = x - half_size, y - half_size
            for u, v, w in prism(ox, oy, z - 1, size, size, 3):
                self.remove_block(u, v, w, user = True)
            self.create_explosion_effect(Vertex3(x, y, z))
        
        def create_falling_block(self, x, y, size, height):
            self.set_block_color(FALLING_BLOCK_COLOR)
            half_size = int(ceil(size / 2.0))
            ox, oy = x - half_size, y - half_size
            for u, v, w in prism(ox, oy, FALLING_BLOCK_Z, size, size, height):
                self.build_block(u, v, w, FALLING_BLOCK_COLOR)
            self.remove_block(ox, oy, FALLING_BLOCK_Z)
            
            z = self.map.get_z(x, y)
            eta = fall_eta(z - FALLING_BLOCK_Z)
            reactor.callLater(eta, self.falling_block_collide, x, y, z, size)
        
        def set_block_color(self, color):
            set_color.value = make_color(*color)
            set_color.player_id = 32
            self.send_contained(set_color, save = True)
        
        def remove_block(self, x, y, z, user = False):
            if z >= 63:
                return False
            if not self.map.get_solid(x, y, z):
                return False
            self.map.remove_point(x, y, z)
            block_action.value = DESTROY_BLOCK
            block_action.player_id = 32
            block_action.x = x
            block_action.y = y
            block_action.z = z
            self.send_contained(block_action, save = True)
            return True
        
        def build_block(self, x, y, z, color, force = False):
            if force:
                self.remove_block(x, y, z)
            if not self.map.get_solid(x, y, z):
                self.map.set_point(x, y, z, color)
                block_action.value = BUILD_BLOCK
                block_action.player_id = 32
                block_action.x = x
                block_action.y = y
                block_action.z = z
                self.send_contained(block_action, save = True)
                return True
            return False
    
    class BossConnection(connection):
        regenerating = False
        trapped = False
        got_water_damage = False
        grabbed_by = None
        last_hit = None
        regen_loop = None
        
        def __init__(self, *arg, **kw):
            connection.__init__(self, *arg, **kw)
            self.regen_loop = LoopingCall(self.regen_cycle)
        
        def regen_cycle(self):
            if (not self.regenerating or self.god or
                self.world_object is None or self.world_object.dead):
                self.regen_loop.stop()
                return
            last_hit = self.last_hit
            if last_hit and reactor.seconds() - last_hit < REGEN_ONSET:
                return
            if self.hp < 100 - REGEN_AMOUNT:
                self.set_hp(self.hp + REGEN_AMOUNT, type = FALL_KILL)
            else:
                self.refill()
                self.regen_loop.stop()
        
        def get_spawn_location(self):
            if self.protocol.boss and self.world_object and not self.trapped:
                return self.world_object.position.get()
            return connection.get_spawn_location(self)
        
        def get_respawn_time(self):
            if self.protocol.boss:
                return 2 if self.trapped else RESPAWN_TIME
            return connection.get_respawn_time(self)
        
        def on_spawn(self, pos):
            if self.trapped:
                self.send_chat('You were eaten by a giant squid :( Pray your '
                    'friends can get you out of this one.')
                self.set_location(self.protocol.boss.origin.get())
            return connection.on_spawn(self, pos)
        
        def on_reset(self):
            self.regenerating = False
            self.trapped = False
            self.got_water_damage = False
            self.grabbed_by = None
            self.last_hit = None
            if self.regen_loop and self.regen_loop.running:
                self.regen_loop.stop()
            connection.on_reset(self)
        
        def on_disconnect(self):
            if self.regen_loop and self.regen_loop.running:
                self.regen_loop.stop()
            self.regen_loop = None
            connection.on_disconnect(self)
        
        def on_kill(self, killer, type, grenade):
            if self.protocol.boss:
                if self.grabbed_by:
                    self.grabbed_by.grabbed_player = None
                self.grabbed_by = None
                if (self.trapped or self.got_water_damage and 
                    self.protocol.boss and not self.protocol.boss.dead and
                    self.protocol.boss.head):
                    self.trapped = True
                else:
                    self.send_chat('You died! Yell at your friends to walk '
                        'over you to revive you.')
            connection.on_kill(self, killer, type, grenade)
        
        def on_weapon_set(self, value):
            if self.protocol.boss and self.regenerating:
                self.weapon = value
                self.set_weapon(self.weapon, no_kill = True)
                self.spawn(self.world_object.position.get())
                return False
            return connection.on_weapon_set(self, value)
        
        def on_orientation_update(self, x, y, z):
            if self.protocol.hp_bar and self.protocol.hp_bar.shown:
                self.protocol.hp_bar.update_for_player(self, (x, y, z))
            connection.on_orientation_update(self, x, y, z)
        
        def on_position_update(self):
            if not self.protocol.boss_ready:
                connection.on_position_update(self)
                return
            if (not self.world_object.dead and not self.grabbed_by
                and not self.trapped):
                for player in self.protocol.players.values():
                    if player is not self and player.world_object.dead:
                        pos = player.world_object.position
                        if vector_collision(self.world_object.position, pos):
                            player.spawn(pos.get())
            if self.protocol.hp_bar and self.protocol.hp_bar.shown:
                self.protocol.hp_bar.update_for_player(self)
            connection.on_position_update(self)
        
        def on_block_build_attempt(self, x, y, z):
            if self.trapped:
                return False
            return connection.on_block_build(self, x, y, z)
        
        def on_block_destroy(self, x, y, z, mode):
            if self.trapped:
                return False
            if self.protocol.boss:
                if self.protocol.boss.on_block_destroy(x, y, z, mode) == False:
                    return False
            return connection.on_block_destroy(self, x, y, z, mode)
        
        def on_block_removed(self, x, y, z):
            if self.protocol.boss:
                self.protocol.boss.on_block_removed(x, y, z)
            connection.on_block_removed(self, x, y, z)
        
        def on_hit(self, hit_amount, hit_player, type, grenade):
            self.last_hit = reactor.seconds()
            if self.regenerating and not self.regen_loop.running:
                self.regen_loop.start(REGEN_FREQUENCY)
            if self.protocol.boss_ready:
                if self is hit_player and self.hp:
                    if hit_amount >= self.hp:
                        return self.hp - 1
            return connection.on_hit(self, hit_amount, hit_player, type, grenade)
        
        def on_fall(self, damage):
            if self.grabbed_by or self.regenerating:
                return False
            self.last_hit = reactor.seconds()
            if self.regenerating and not self.regen_loop.running:
                self.regen_loop.start(REGEN_FREQUENCY)
            return connection.on_fall(self, damage)
    
    return BossProtocol, BossConnection