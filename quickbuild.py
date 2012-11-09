"""
Build structures instantly, and easily record new ones!

See: https://github.com/infogulch/pyspades-userscripts/wiki/Quickbuild
"""

from commands import add, alias, admin
from math import floor, atan2, pi
from pyspades.constants import *
from pyspades.contained import BlockAction, SetColor
from pyspades.common import make_color
from itertools import imap, izip
import json
import cbc
import collections
import itertools
import os
import re
from avx import AVX

QB_DIR = './qb'

DIRT_COLOR = (103, 64, 40)

EAST, SOUTH, WEST, NORTH = xrange(4)

# recording modes
Q_STOPPED, Q_RECORDING, Q_COPYING, Q_ORIGINATING = xrange(4)

# build modes
Q_OFF, Q_BUILD, Q_BUILD_RECORDED = xrange(3)

if not os.path.exists(QB_DIR):
    os.makedirs(QB_DIR)

def shift_origin_all(dct, new_origin):
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

def shift_origin(coords, new_origin):
    return shift_origin_all(((coords, None),), new_origin).next()[0]

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
    return rotate_all(((coords, None),), fm, to).next()[0]

def get_blocks(vmap, xyz1, xyz2, colors = False):
    p = [xrange(a,b+1) for a,b in map(sorted, zip(xyz1, xyz2))]
    for xyz in itertools.product(*p):
        solid, color = vmap.get_point(*xyz)
        if solid:
            yield xyz, color if colors else None

def qb_fname(name):
    if not re.match('\w+$', name):
        return None
    fname = '%s/%s.avx' % (QB_DIR, name)
    return fname

def qb_get_info(fname):
    try:
        settings = json.load(open(fname, 'r'))
    except (IOError, ValueError), e:
        settings = {}
    return settings

def qb_update_info(fname, info):
    current = qb_get_info(fname)
    current.update(info)
    json.dump(current, open(fname, 'w'))

# Use these commands to create quickbuild structures.
@admin
def qbrecord(connection, colored = ''):
    if connection.qb_recording:
        connection.qb_recording = Q_STOPPED
        return 'No longer recording.'
    else:
        s_colors = 'WITHOUT'
        s_origin = ' First block sets the origin and orientation.'
        connection.qb_recording = Q_RECORDING
        connection.qb_record_colors = colored.lower() == 'colored'
        if connection.qb_record_colors:
            s_colors = 'WITH'
        if connection.qb_record_origin:
            s_origin = ''
        return 'Now recording %s colors.%s' % (s_colors, s_origin)

@admin
def qbsave(connection, name, cost = None, *description):
    fname = qb_fname(name)
    if not fname:
        return 'Invalid save name. Only alphanumeric characters allowed.'
    if not connection.qb_recorded:
        return 'Nothing is recorded yet!'
    
    shift = map(min, zip(*connection.qb_recorded.iterkeys()))
    origin = [-x for x in shift]
    
    info = {'colored': connection.qb_record_colors
          , 'origin': origin}
    if cost is not None:
        info['cost'] = int(cost)
    if description:
        info['description'] = ' '.join(description)
    
    qb_update_info(fname + '.txt', info)
    
    recorded = dict(shift_origin_all(connection.qb_recorded, shift))
    AVX.fromsparsedict(recorded, info['colored']).save(fname)
    
    return 'Saved buffer to %s.avx' % name

@admin
def qbload(connection, name):
    fname = qb_fname(name)
    if not fname:
        return 'Invalid load name. Only alphanumeric characters allowed.'
    qbclear(connection)
    
    settings = qb_get_info(fname + '.txt')
    
    if not settings.has_key('origin'):
        return 'Invalid information for file %s' % name
    
    recorded = AVX.fromfile(fname).tosparsedict()
    
    connection.qb_recorded = dict(shift_origin_all(recorded, settings['origin']))
    
    return 'Loaded %s.avx to buffer.' % name

@admin
def qbprint(connection):
    print connection.qb_recorded

@admin
def qbrotate(connection, amount):
    amount = int(amount)
    if amount in xrange(4):
        connection.qb_recorded = dict(rotate_all(connection.qb_recorded, 0, amount))

@admin
def qbshiftorigin(connection):
    if not connection.qb_recording:
        return 'You must be recording first.'
    if not connection.qb_record_origin or not connection.qb_recorded:
        return 'Nothing recorded yet!'
    if connection.qb_recording == Q_ORIGINATING:
        connection.qb_recording = Q_STOPPED
        return 'No longer changing the origin. Recording stopped.'
    connection.qb_recording = Q_ORIGINATING
    return 'Place a block to mark the new origin AND orientation!'

@admin
def qbcopy(connection, colored = ''):
    qbclear(connection)
    connection.qb_recording = Q_COPYING
    connection.qb_record_colors = colored.lower() == 'colored'
    s_colors = 'WITH' if connection.qb_record_colors else 'WITHOUT'
    return 'Copying %s colors. Place first corner block. This sets the the origin and orientation.' % s_colors

@admin
def qbclear(connection):
    message = 'Quickbuild recorded blocks cleared.'
    if connection.qb_recording:
        message += ' Recording stopped.'
    connection.qb_recorded.clear()
    connection.qb_record_origin = None
    connection.qb_record_colors = False
    connection.qb_recording = Q_STOPPED
    return message

@alias('br')
@admin
def buildrecorded(connection):
    message = 'The next block you place will build the recorded structure.'
    if connection.qb_recording != Q_STOPPED:
        message += ' Recording stopped.'
    connection.qb_recording = Q_STOPPED
    connection.qb_building = Q_BUILD_RECORDED
    connection.qb_info = None
    return message

# Build a structure.
@alias('b')
def build(connection, name = None):
    if not connection.quickbuild_allowed:
        return 'You are not allowed to build'
    if name is None:
        connection.qb_building = Q_OFF
        connection.qb_info = None
        sts = ''
        for fname in glob.iglob(QB_DIR + '/*.avx.txt'):
            info = qb_get_info(fname)
            if not info.has_key('cost'):
                continue
            st = ', %s(%i)' % (name, info['cost'])
            if len(sts + st) >= MAX_CHAT_SIZE:
                connection.send_chat(sts[2:])
                sts = ''
            sts += st
        connection.send_chat(sts[2:])
        return 'QuickBuild: Available structures. NAME(cost). /build NAME. You have %i points.' % connection.qb_points
    else:
        if connection.qb_info != None:
            connection.qb_building = Q_OFF
            connection.qb_info = None
            return "No longer building."
        fname = qb_fname(name)
        if fname is None:
            return 'Invalid structure name'
        info = qb_get_info(fname + '.txt')
        if not connection.god and not info.has_key('cost'):
            return 'Invalid structure'
        cost = info.get('cost', 0)
        info['name'] = name
        if connection.qb_points >= cost or connection.god:
            connection.qb_info = info
            connection.qb_building = Q_BUILD
            return 'The next block you place will build a %s.' % info.get('description', name)
        else:
            return ('You need %i more points if you want to build %s: %s.' 
                % (cost-connection.qb_points, name, info.get('description', name)))

add(build)
add(buildrecorded)

add(qbrecord)
add(qbsave)
add(qbload)
add(qbclear)
# add(qbprint)

add(qbcopy)
add(qbrotate)
add(qbshiftorigin)

def apply_script(protocol, connection, config):
    protocol, connection = cbc.apply_script(protocol, connection, config)
    
    class BuildConnection(connection):
        def __init__(self, *arg, **kw):
            connection.__init__(self, *arg, **kw)
            self.quickbuild_allowed = True
            self.qb_info = None
            self.qb_points = 0
            self.qb_building = Q_OFF
            
            self.qb_recording = Q_STOPPED
            self.qb_record_colors = False
            self.qb_record_origin = None
            self.qb_record_dir = None
            self.qb_recorded = dict()
        
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
            connection.on_block_removed(self, x, y, z)
            if self.qb_recording and self.qb_recorded:
                xyz = shift_origin((x,y,z),self.qb_record_origin)
                self.qb_recorded.pop(xyz, 'Not popped')
        
        def quickbuild_block_build(self, x, y, z):
            if self.qb_recording:
                if self.qb_record_origin is None:
                    self.qb_record_origin = (x, y, z)
                    self.qb_record_dir = self.get_direction()
                xyz = shift_origin((x,y,z), self.qb_record_origin)
                xyz = rotate(xyz, self.qb_record_dir, EAST)
                self.qb_recorded[xyz] = self.color if self.qb_record_colors else None
        
        def on_block_build_attempt(self, x, y, z):
            cont = True
            if self.qb_recording and not self.qb_record_origin:
                self.qb_record_origin = (x, y, z)
                self.qb_record_dir = self.get_direction()
                if self.qb_recording == Q_COPYING:
                    self.send_chat('Now place the opposite corner block!')
                else:
                    self.send_chat('Now start building!')
                cont = False
            elif self.qb_recording == Q_COPYING:
                blocks = get_blocks(self.protocol.map, self.qb_record_origin, (x,y,z), self.qb_record_colors)
                blocks = shift_origin_all(blocks, self.qb_record_origin)
                blocks = rotate_all(blocks, self.qb_record_dir, EAST)
                self.qb_recorded = dict(blocks)
                self.qb_recording = Q_STOPPED
                self.send_chat('Copied area to buffer!')
                cont = False
            
            if self.qb_building:
                if self.qb_building == Q_BUILD_RECORDED:
                    structure = rotate_all(self.qb_recorded, EAST, self.get_direction())
                    color = DIRT_COLOR if self.qb_record_colors else self.color
                else:
                    self.qb_points -= self.qb_info.get('cost', 0)
                    vx = AVX.fromfile(qb_fname(self.qb_info['name']))
                    structure = vx.tosparsedict()
                    structure = shift_origin_all(structure, self.qb_info['origin'])
                    structure = rotate_all(structure, EAST, self.get_direction())
                    color = DIRT_COLOR if vx.has_colors else self.color
                self.protocol.cbc_add(self.quickbuild_generator((x, y, z), structure, color))
                self.qb_building = Q_OFF
                self.qb_info = None
                self.send_chat('Building structure!')
                cont = False
            
            if self.qb_recording == Q_ORIGINATING:
                new_origin = (x,y,z)
                shift = shift_origin(self.qb_record_origin, new_origin)
                self.qb_recorded = dict(shift_origin_all(self.qb_recorded, shift))
                self.qb_record_origin = new_origin
                self.send_chat('New origin saved!')
                cont = False
            
            if not cont:
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
            
            if not isinstance(structure, dict):
                structure = dict(structure)
            
            for xyz, color in structure.iteritems():
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