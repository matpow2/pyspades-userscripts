from commands import add, alias, admin
from math import floor, atan2, pi
from pyspades.constants import *
from pyspades.contained import BlockAction, SetColor
from pyspades.common import make_color
from collections import OrderedDict
from itertools import imap, izip
import json
import cbc
import collections
import itertools
import os
from avx import AVX

QB_DIR = './qb'

DIRT_COLOR = (103, 64, 40)

EAST, SOUTH, WEST, NORTH = xrange(4)

if not os.path.exists(QB_DIR):
    os.makedirs(QB_DIR)

def shift_origin(dct, new_origin):
    # dct is a dict (or another 2-tuple iterable) of tuple, color
    # returns a 2-tuple iterator
    # new_origin is relative to the current origin.
    # the old origin is now the inverse of new_origin
    new_origin = tuple(new_origin)
    shift = lambda tpl: tuple(a-b for a,b in zip(tpl, new_origin))
    if isinstance(dct, dict):
        dct = dct.iteritems()
    for k,v in dct:
        yield shift(k), v

def rotate_all(dct, fm, to):
    # dct is a dict (or 2-tuple iterator) of tuple, color
    # returns a 2-tuple iterator that shifts the original dict about the origin (0,0,0)
    # assumes y increases to the south
    amt = (to - fm) % 4
    if amt == 0:
        rot = lambda t: t
    elif amt == 1:
        rot = lambda t: (-t[1],  t[0]) + t[2:]
    elif amt == 2:
        rot = lambda t: (-t[0], -t[1]) + t[2:]
    elif amt == 3:
        rot = lambda t: ( t[1], -t[0]) + t[2:]
    if isinstance(dct, dict):
        dct = dct.iteritems()
    for k,v in dct:
        yield rot(k), v

def rotate(coords, fm, to):
    return rotate_all({coords: None}, fm, to).next()[0]

# Use these commands to create quickbuild structures.
@admin
def qbrecord(connection, colored = ''):
    if connection.qb_recording:
        connection.qb_recording = 0
        connection.send_chat('You are no longer recording.')
    else:
        connection.qb_recording = (colored.lower() == 'colored') + 1
        colors = ' with colors' if connection.qb_recording == 2 else ''
        connection.send_chat('You are now recording%s. First block marks the origin.' % colors)

@admin
def qbsave(connection, name):
    if not name.isalnum():
        connection.send_chat('Invalid save name. Only alphanumeric characters allowed.')
        return
    fname = '%s/%s.avx' % (QB_DIR, name)
    
    shift = map(min, zip(*connection.qb_recorded.iterkeys()))
    origin = [-x for x in shift]
    
    settings = {'colored': connection.qb_recording == 2, 'origin': origin}
    
    json.dump(settings, open(fname + '.txt', 'w'))
    
    recorded = dict(shift_origin(connection.qb_recorded, shift))
    AVX.fromsparsedict(recorded, settings['colored']).save(fname)
    
    connection.send_chat('Saved to %s.avx' % name)

@admin
def qbload(connection, name):
    if not name.isalnum():
        connection.send_chat('Invalid load name. Only alphanumeric characters allowed.')
        return
    fname = '%s/%s.avx' % (QB_DIR, name)
    
    settings = json.load(open(fname + '.txt', 'r'))
    
    recorded = AVX.fromfile(fname).tosparsedict()
    
    connection.qb_recorded = OrderedDict(shift_origin(recorded, settings['origin']))
    
    connection.send_chat('Loaded %s.avx to recorded buffer!' % name)

@admin
def qbprint(connection):
    print sorted(connection.qb_recorded.keys())

@admin
def qbrotate(connection, amount):
    amount = int(amount)
    if amount in (NORTH, SOUTH, EAST, WEST):
        connection.qb_recorded = OrderedDict(rotate_all(connection.qb_recorded, EAST, amount))

@admin
def qbshiftorigin(connection):
    pass

@admin
def qbclear(connection):
    connection.qb_recorded.clear()
    connection.qb_record_origin = None
    connection.qb_recording = 0
    connection.send_chat('Quickbuild recorded blocks cleared.')

@alias('br')
@admin
def buildrecorded(connection):
    connection.qb_recording = 0
    connection.qb_building = 2
    connection.qb_info = None
    connection.send_chat('The next block you place will build the recorded structure.')

# Build a structure.
@alias('b')
def build(connection, structure = None):
    if not connection.quickbuild_allowed:
        connection.send_chat('You are not allowed to build')
        return
    builds = connection.protocol.config.get('build', {})
    if structure is None:
        connection.qb_building = 0
        connection.qb_info = None
        connection.send_chat('QuickBuild: Available structures. NAME(cost). /build NAME. You have %i points.' % connection.qb_points)
        sts = ''
        for name, info in builds.iteritems():
            st = ', %s(%i)' % (name, info.get('cost',0))
            if len(sts + st) >= MAX_CHAT_SIZE:
                connection.send_chat(sts[2:])
                sts = ''
            sts += st
        connection.send_chat(sts[2:])
    else:
        if connection.qb_info != None:
            connection.qb_building = 0
            connection.qb_info = None
            connection.send_chat("No longer building.")
            return
        name = structure.lower()
        if not builds.has_key(name):
            connection.send_chat('The structure that you entered is invalid: %s' % name)
            return
        info = builds[name]
        cost = info.get('cost', 0)
        if connection.qb_points >= cost or connection.god:
            connection.qb_info = info
            connection.send_chat('The next block you place will build a %s.' % info.get('description', name))
            connection.qb_building = 1
        else:
            connection.send_chat('You need %i more points if you want to build %s: %s.' 
                % (cost-connection.qb_points, name, info.get('description', name)))

add(build)
add(buildrecorded)

add(qbrecord)
add(qbsave)
add(qbload)
add(qbprint)

add(qbclear)

add(qbrotate)

def apply_script(protocol, connection, config):
    protocol, connection = cbc.apply_script(protocol, connection, config)
    
    class BuildConnection(connection):
        def __init__(self, *arg, **kw):
            connection.__init__(self, *arg, **kw)
            self.quickbuild_allowed = True
            self.qb_info = None
            self.qb_points = 0
            self.qb_building = 0
            
            self.qb_recording = 0
            self.qb_record_origin = None
            self.qb_record_dir = None
            self.qb_recorded = OrderedDict()
        
        def get_direction(self):
            orientation = self.world_object.orientation
            return int(round(atan2(orientation.y, orientation.x) / pi * 2) % 4)
        
        def on_kill(self, killer, type, grenade):
            ret = connection.on_kill(self, killer, type, grenade)
            if ret is None:
                if killer is not None and self.team is not killer.team and self != killer:
                    killer.qb_points += 1
            return ret
        
        def on_line_build(self, points):
            for x, y, z in points:
                self.quickbuild_block_build(x, y, z)
            return connection.on_line_build(self, points)
        
        def on_block_build(self, x, y, z):
            self.quickbuild_block_build(x, y, z)
            return connection.on_block_build(self, x, y, z)
        
        def on_block_removed(self, x, y, z):
            if self.qb_recording != 0:
                x, y, z = [a-o for a,o in zip((x,y,z),self.qb_record_origin)]
                self.qb_recorded.pop((x,y,z), None)
        
        def quickbuild_block_build(self, x, y, z):
            if self.qb_recording:
                if self.qb_record_origin is None:
                    self.qb_record_origin = (x, y, z)
                    self.qb_record_dir = self.get_direction()
                xyz = tuple([a-b for a,b in zip((x,y,z), self.qb_record_origin)])
                xyz = rotate(xyz, self.qb_record_dir, EAST)
                self.qb_recorded[xyz] = self.color if self.qb_recording == 2 else None
        
        def on_block_build_attempt(self, x, y, z):
            if self.qb_building:
                if self.qb_building == 2:
                    structure = rotate_all(self.qb_recorded, EAST, self.get_direction())
                    color = DIRT_COLOR if self.qb_recording == 2 else self.color
                else:
                    file = QB_DIR + '/' + self.qb_info['file']
                    self.qb_points -= self.qb_info['cost']
                    vx = AVX.fromfile(file)
                    origin = json.load(open(file + '.txt', 'r')).get('origin', (0,0,0))
                    structure = vx.tosparsedict()
                    structure = shift_origin(structure, origin)
                    structure = rotate_all(structure, EAST, self.get_direction())
                    color = DIRT_COLOR if vx.has_colors else self.color
                # structure is an iterator
                self.send_chat('Building structure.')
                self.protocol.cbc_add(self.quickbuild_generator((x, y, z), structure, color))
                self.qb_building = 0
                self.qb_info = None
                return False
            elif self.qb_recording and self.qb_record_origin is None:
                self.qb_record_origin = (x, y, z)
                self.qb_record_dir = self.get_direction()
                return False
            return connection.on_block_build_attempt(self, x, y, z)
        
        def quickbuild_generator(self, origin, structure, default_color):
            map = self.protocol.map
            protocol = self.protocol
            
            splayer = cbc.ServerPlayer()
            
            block_action = BlockAction()
            block_action.value = BUILD_BLOCK
            block_action.player_id = splayer.player_id
            
            set_color = SetColor()
            set_color.value = make_color(*default_color)
            set_color.player_id = splayer.player_id
            pcolor = default_color
            
            protocol.send_contained(set_color, save = True)
            
            for xyz, color in structure:
                x, y, z = [a+b for a,b in zip(xyz, origin)]
                if (x < 0 or x >= 512 or y < 0 or y >= 512 or z < 0 or z >= 62):
                    continue
                if map.get_solid(x, y, z):
                    continue
                color = color or default_color
                if color != pcolor:
                    set_color.value = make_color(*color)
                    protocol.send_contained(set_color, save = True)
                    pcolor = color
                    yield 1, 0
                self.on_block_build(x, y, z)
                block_action.x, block_action.y, block_action.z = x, y, z
                protocol.send_contained(block_action, save = True)
                map.set_point(x, y, z, pcolor)
                yield 1, 0
    
    return protocol, BuildConnection