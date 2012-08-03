from commands import add, admin, alias
from math import floor, atan2, pi
from pyspades.constants import *
from pyspades.contained import BlockAction, SetColor
from cbc import cbc
import collections
import itertools

QUICKBUILD_WALL = ((0, 0, 0), (0, 1, 0), (0, 1, 1), (0, 2, 0), (0, 2, 1)
                 , (0, 3, 0), (0, 3, 1), (0, 0, 1), (0, -1, 0), (0, -1, 1)
                 , (0, -2, 0), (0, -2, 1), (0, -3, 0), (0, -3, 1), (-1, 3, 0)
                 , (-1, 3, 1), (-2, 3, 0), (-2, 3, 1), (-1, -3, 0), (-1, -3, 1)
                 , (-2, -3, 0), (-2, -3, 1), (1, 7, 0))
QUICKBUILD_BUNKER = ((0, 0, 0), (-1, 0, 0), (-1, 0, 1), (-1, 0, 2), 
                     (0, 0, 2), (1, 0, 0), (1, 0, 1), (1, 0, 2), 
                     (2, 0, 0), (2, 0, 2), (-2, 0, 2), (-2, 0, 0), 
                     (3, 0, 0), (3, 0, 1), (3, 0, 2), (-3, 0, 0), 
                     (-3, 0, 1), (-3, 0, 2), (3, 0, 3), (2, 0, 3), 
                     (1, 0, 3), (0, 0, 3), (-1, 0, 3), (-2, 0, 3), 
                     (-3, 0, 3), (-3, -1, 0), (-3, -1, 1), (-3, -1, 2), 
                     (-3, -1, 3), (-3, -2, 3), (-3, -2, 2), (-3, -2, 1), 
                     (-3, -2, 0), (-3, -3, 0), (-3, -3, 1), (-3, -3, 2), 
                     (-3, -3, 3), (-2, -1, 3), (-2, -2, 3), (-2, -3, 3), 
                     (-1, -1, 3), (-1, -2, 3), (-1, -3, 3), (0, -1, 3), 
                     (0, -2, 3), (0, -3, 3), (1, -1, 3), (1, -2, 3), 
                     (1, -3, 3), (2, -1, 3), (2, -2, 3), (2, -3, 3), 
                     (3, -3, 3), (3, -3, 0), (3, -3, 1), (3, -3, 2), 
                     (3, -2, 3), (3, -2, 0), (3, -2, 1), (3, -2, 2), 
                     (3, -1, 0), (3, -1, 1), (3, -1, 2), (3, -1, 3), (0, 1, 0), (2, 1, 0), (-2, 1, 0),
                     (1, -1, 0), (1, -1, 1), (1, -1, 2), (-1, -1, 0), (-1, -1, 1), (-1, -1, 2),
                     (2, -3, 0), (2, -3, 1), (2, -3, 2), (-2, -3, 0), (-2, -3, 1), (-2, -3, 2))
QUICKBUILD_TENT = ((0,0,1), (0,0,2), (1,0,0), (1,0,1), (-1,0,0), (-1,0,1), (2,0,0), (-2,0,0), (0,1,0),
                   (0,1,1),(0,-1,0),(0,-1,1), (0,2,0), (0,-2,0))
QUICKBUILD_MOBILEFORT = ((-2, 0, 0), (-1, 0, 0), (1, 0, 0), (2, 0, 0),
             (-2, -4, 0), (-1, -4, 0), (1, -4, 0), (2, -4, 0),
             (-2, -1, 0), (2, -1, 0), (-2, -2, 0), (2, -2, 0), (-2, -3, 0), (2, -3, 0),
             (-2, 0, 1), (0, 0, 1), (2, 0, 1),
             (-2, -4, 1), (-1, -4, 1), (1, -4, 1), (2, -4, 1),
             (-2, -2, 1), (2, -2, 1),
             (-2, 0, 2), (-1, 0, 2), (0, 0, 2), (1, 0, 2), (2, 0, 2),
             (-2, -4, 2), (-1, -4, 2), (0, -4, 2), (1, -4, 2), (2, -4, 2),
             (-2, -1, 2), (2, -1, 2), (-2, -2, 2), (2, -2, 2), (-2, -3, 2), (2, -3, 2),
             (-2,  0, 3), (-1,  0, 3), (0,  0, 3), (1,  0, 3), (2,  0, 3),
             (-2, -1, 3), (-1, -1, 3), (0, -1, 3), (1, -1, 3), (2, -1, 3),
             (-2, -2, 3), (-1, -2, 3), (0, -2, 3), (1, -2, 3), (2, -2, 3),
             (-2, -3, 3), (-1, -3, 3), (0, -3, 3), (1, -3, 3), (2, -3, 3),
             (-2, -4, 3), (-1, -4, 3), (0, -4, 3), (1, -4, 3), (2, -4, 3))
QUICKBUILD_BIGWALL = ((0, 0, 0),(-1, 0, 0),(-1, 0, 1),(-2, 0, 0),(-2, 0, 1),(-3, 0, 0),(-3, 0, 1),(0, 0, 1),
                      (1, 0, 0),(1, 0, 1), (2, 0, 0),(2, 0, 1),(3, 0, 0),(3, 0, 1),(-3, -1, 0),(-3, -1, 1),
                      (-3, -2, 0),(-3, -2, 1),(3, -1, 0),(3, -1, 1),(3, -2, 0),(3, -2, 1),(0, 0, 2),(-1, 0, 2),
                      (-2, 0, 2),(-3, 0, 2),(1, 0, 2),(2, 0, 2),(3, 0, 2),(-3, -1, 2),(-3, -2, 2),(3, -1, 2),
                      (3, -2, 2),(0, -1, 0),(-1, -1, 0),(-2, -1, 0),(-3, -1, 0),(1, -1, 0),(2, -1, 0),(3, -1, 0),
                      (-3, -3, 1), (3, -3, 1))
QUICKBUILD_DEFENSEWALL =((0, 0, 0), (-1, 0, 0), (-1, 0, 1), (-2, 0, 0), (-2, 0, 1), 
                   (-3, 0, 0), (-3, 0, 1), (0, 0, 1), (1, 0, 0), (1, 0, 1),
                   (2, 0, 0), (2, 0, 1), (3, 0, 0), (3, 0, 1), (-3, -1, 0), (-3, -1, 1), (-3, -2, 0),
                   (-3, -2, 1),(3, -1, 0), (3, -1, 1), (3, -2, 0), (3, -2, 1),
                         (0, 0, 2), (-1, 0, 2), (-1, 0, 3), (-2, 0, 2), (-2, 0, 3), 
                   (-3, 0, 2), (-3, 0, 3), (0, 0, 3), (1, 0, 2), (1, 0, 3),
                   (2, 0, 2), (2, 0, 3), (3, 0, 2), (3, 0, 3), (-3, -1, 2), (-3, -1, 3), (-3, -2, 2),
                   (-3, -2, 3),(3, -1, 2), (3, -1, 3), (3, -2, 2), (3, -2, 3),
                   (0,-1,0),(1,-1,0),(-1,-1,0),(2,-1,0),(-2,-1,0),
                   (0,-1,1),(1,-1,1),(-1,-1,1),(2,-1,1),(-2,-1,1))
QUICKBUILD_FORT = ((0,0,0),(0,0,1),(0,0,2),(1,0,0),(1,0,1),(1,0,2),(-1,0,0),(-1,0,1),(-1,0,2),
                   (2,0,0),(2,0,1),(2,0,2),(-2,0,0),(-2,0,1),(-2,0,2),(3,0,0),(3,0,1),(3,0,2),
                   (-3,0,0),(-3,0,1),(-3,0,2),(4,0,0),(4,0,1),(4,0,2),(-4,0,0),(-4,0,1),(-4,0,2),
                   (0,1,0),(0,1,1),(0,1,2),(1,1,0),(1,1,1),(1,1,2),(-1,1,0),(-1,1,1),(-1,1,2),
                   (2,1,0),(2,1,1),(2,1,2),(-2,1,0),(-2,1,1),(-2,1,2),(3,1,0),(3,1,1),(3,1,2),
                   (-3,1,0),(-3,1,1),(-3,1,2),(4,1,0),(4,1,1),(4,1,2),(-4,1,0),(-4,1,1),(-4,1,2),
                   (0,2,0),(0,2,1),(0,2,2),(1,2,0),(1,2,1),(1,2,2),(-1,2,0),(-1,2,1),(-1,2,2),
                   (2,2,0),(2,2,1),(2,2,2),(-2,2,0),(-2,2,1),(-2,2,2),(3,2,0),(3,2,1),(3,2,2),
                   (-3,2,0),(-3,2,1),(-3,2,2),(4,2,0),(4,2,1),(4,2,2),(-4,2,0),(-4,2,1),(-4,2,2),
                   (0,3,0),(1,3,0),(-1,3,0),(2,3,0),(-2,3,0),(3,3,0),(-3,3,0),(4,3,0),(-4,3,0),
                   (0,2,3),(2,2,3),(4,2,3),(-2,2,3),(-4,2,3))
QUICKBUILD_BRIDGE = ((0, 0, 0), (1, 0, 0), (-1, 0, 0), (-1, 1, 0), 
                     (0, 1, 0), (1, 1, 0), (1, 2, 0), (0, 2, 0), 
                     (-1, 2, 0), (-1, 3, 0), (0, 3, 0), (1, 3, 0), 
                     (1, 4, 0), (0, 4, 0), (-1, 4, 0), (-1, 5, 0), 
                     (0, 5, 0), (1, 5, 0), (1, 6, 0), (0, 6, 0), 
                     (-1, 6, 0), (-1, 7, 0), (0, 7, 0), (1, 7, 0), 
                     (1, 8, 0), (0, 8, 0), (-1, 8, 0), (-1, 9, 0), 
                     (0, 9, 0), (1, 9, 0), (1, 10, 0), (0, 10, 0), 
                     (-1, 10, 0), (-1, 11, 0), (0, 11, 0), (1, 11, 0), 
                     (1, 12, 0), (0, 12, 0), (-1, 12, 0), (-1, 13, 0), 
                     (0, 13, 0), (1, 13, 0), (1, 14, 0), (0, 14, 0), 
                     (-1, 14, 0), (-1, 15, 0), (0, 15, 0), (1, 15, 0), 
                     (1, 16, 0), (0, 16, 0), (-1, 16, 0), (-1, 17, 0), 
                     (0, 17, 0), (1, 17, 0), (1, 18, 0), (0, 18, 0), 
                     (-1, 18, 0), (-1, 19, 0), (0, 19, 0), (1, 19, 0), 
                     (1, 20, 0), (0, 20, 0), (-1, 20, 0), (-1, 21, 0), 
                     (0, 21, 0), (1, 21, 0), (1, 22, 0), (0, 22, 0), 
                     (-1, 22, 0), (-1, 23, 0), (0, 23, 0), (1, 23, 0), 
                     (0, 24, 0), (1, 24, 0), (-1, 24, 0), (-1, 25, 0), 
                     (0, 25, 0), (1, 25, 0),
                     (-1, 1, 1), (0, 1, 1), (1, 1, 1), (1, 2, 1), (0, 2, 1), 
                     (-1, 2, 1), (-1, 3, 1), (0, 3, 1), (1, 3, 1), 
                     (1, 4, 1), (0, 4, 1), (-1, 4, 1), (-1, 5, 1), 
                     (0, 5, 1), (1, 5, 1), (1, 6, 1), (0, 6, 1), 
                     (-1, 6, 1), (-1, 7, 1), (0, 7, 1), (1, 7, 1), 
                     (1, 8, 1), (0, 8, 1), (-1, 8, 1), (-1, 9, 1), 
                     (0, 9, 1), (1, 9, 1), (1, 10, 1), (0, 10, 1), 
                     (-1, 10, 1), (-1, 11, 1), (0, 11, 1), (1, 11, 1), 
                     (1, 12, 1), (0, 12, 1), (-1, 12, 1), (-1, 13, 1), 
                     (0, 13, 1), (1, 13, 1), (1, 14, 1), (0, 14, 1), 
                     (-1, 14, 1), (-1, 15, 1), (0, 15, 1), (1, 15, 1), 
                     (1, 16, 1), (0, 16, 1), (-1, 16, 1), (-1, 17, 1), 
                     (0, 17, 1), (1, 17, 1), (1, 18, 1), (0, 18, 1), 
                     (-1, 18, 1), (-1, 19, 1), (0, 19, 1), (1, 19, 1), 
                     (1, 20, 1), (0, 20, 1), (-1, 20, 1), (-1, 21, 1), 
                     (0, 21, 1), (1, 21, 1), (1, 22, 1), (0, 22, 1), 
                     (-1, 22, 1), (-1, 23, 1), (0, 23, 1), (1, 23, 1), 
                     (0, 24, 1), (1, 24, 1), (-1, 24, 1), (-1, 25, 1), 
                     (0, 25, 1), (1, 25, 1),
                      (1, 2, 2), (0, 2, 2), 
                     (-1, 2, 2), (-1, 3, 2), (0, 3, 2), (1, 3, 2), 
                     (1, 4, 2), (0, 4, 2), (-1, 4, 2), (-1, 5, 2), 
                     (0, 5, 2), (1, 5, 2), (1, 6, 2), (0, 6, 2), 
                     (-1, 6, 2), (-1, 7, 2), (0, 7, 2), (1, 7, 2), 
                     (1, 8, 2), (0, 8, 2), (-1, 8, 2), (-1, 9, 2), 
                     (0, 9, 2), (1, 9, 2), (1, 10, 2), (0, 10, 2), 
                     (-1, 10, 2), (-1, 11, 2), (0, 11, 2), (1, 11, 2), 
                     (1, 12, 2), (0, 12, 2), (-1, 12, 2), (-1, 13, 2), 
                     (0, 13, 2), (1, 13, 2), (1, 14, 2), (0, 14, 2), 
                     (-1, 14, 2), (-1, 15, 2), (0, 15, 2), (1, 15, 2), 
                     (1, 16, 2), (0, 16, 2), (-1, 16, 2), (-1, 17, 2), 
                     (0, 17, 2), (1, 17, 2), (1, 18, 2), (0, 18, 2), 
                     (-1, 18, 2), (-1, 19, 2), (0, 19, 2), (1, 19, 2), 
                     (1, 20, 2), (0, 20, 2), (-1, 20, 2), (-1, 21, 2), 
                     (0, 21, 2), (1, 21, 2), (1, 22, 2), (0, 22, 2), 
                     (-1, 22, 2), (-1, 23, 2), (0, 23, 2), (1, 23, 2), 
                     (0, 24, 2), (1, 24, 2), (-1, 24, 2), (-1, 25, 2), 
                     (0, 25, 2), (1, 25, 2))
QUICKBUILD_STRUCTURES = (QUICKBUILD_WALL, QUICKBUILD_BUNKER, QUICKBUILD_TENT,
                         QUICKBUILD_MOBILEFORT, QUICKBUILD_BIGWALL, QUICKBUILD_DEFENSEWALL,
                         QUICKBUILD_FORT,QUICKBUILD_BRIDGE)
QUICKBUILD_DESCRIPTION = ('wall', 'bunker', 'tent', 'mobilefort','bigwall','defensewall','fort', 'bridge')

QUICKBUILD_COST = (0, 1, 0, 1, 2, 3, 4, 5)

QB_DIR = './qb'
QB_EXT = 'avx'

EAST, SOUTH, WEST, NORTH = xrange(4)

def shift_origin(list, new_origin):
    # new_origin is relative to the current origin.
    # the old origin is now the inverse of new_origin
    shift = (-n for n in new_origin)
    return [map(sum, zip(xyz, shift)) for xyz in list]

def rotate_all(fm, to, list):
    # list is a list of tuples
    # assumes y increases to the south
    amt = (to - fm) % 4
    lamb = lambda t: t
    if amt == 1:
        lamb = lambda t: (-t[1],  t[0]) + t[2:]
    elif amt == 2:
        lamb = lambda t: (-t[0], -t[1]) + t[2:]
    elif amt == 3:
        lamb = lambda t: ( t[1], -t[0]) + t[2:]
    return itertools.imap(lamb, list)

def rotate_all_dict(fm, to, d):
    return itertools.izip(rotate_all(fm, to, d.iterkeys()), d.itervalues())

def rotate_all_dict_keys(fm, to, d):
    return rotate_all(fm, to, d.iterkeys())

def rotate(fm, to, *tpl):
    return tuple(rotate_all(fm, to, [tpl]))[0]

# Use these commands to create quickbuild structures.
@admin
def qbrecord(connection, colored = ''):
    if connection.qb_recording:
        connection.qb_recording = 0
        connection.send_chat('You are no longer recording.')
    else:
        connection.qb_recording = (colored.lower() == 'colored') + 1
        connection.send_chat('You are now recording. First block marks the origin.')

@admin
def qbsave(connection, name):
    if not name.isalnum():
        connection.send_chat('Invalid save name. Only alphanumeric characters allowed.')
        return
    recorded = shift_origin(connection.qb_recorded, map(min, izip(*connection.qb_recorded)))
    # import avx

@admin
def qbprint(connection):
    print connection.qb_recorded

@admin
def qbrotate(connection, amount):
    amount = int(amount)
    if amount in (NORTH, SOUTH, EAST, WEST):
        connection.qb_recorded = OrderedDict(rotate_all(EAST, amount, connection.qb_recorded))

@admin
def qbshiftorigin(connection):
    pass

@admin
def qbclear(connection):
    connection.qb_recorded.clear()
    connection.qb_record_origin = None
    connection.send_chat('Quickbuild recorded blocks cleared.')

@admin
def qbundo(connection):
    if len(connection.qb_recorded):
        connection.qb_recorded.popitem()
        connection.send_chat('Last recorded item removed.')

@alias('br')
@admin
def buildrecorded(connection):
    connection.qb_recording = 0
    connection.qb_build_recorded = True
    connection.qb_building = True
    connection.send_chat('The next block you place will build the recorded structure.')

# Build a structure.
@alias('b')
def build(connection, structure = None):
    if not connection.quickbuild_allowed:
        connection.send_chat('You are not allowed to build')
        return
    if structure == None:
        connection.qb_building = False
        connection.quickbuild_index = None
        for i in xrange(len(QUICKBUILD_STRUCTURES)):
            connection.send_chat('%i: Build a %s. Requires %i kills.' 
                % (i, QUICKBUILD_DESCRIPTION[i], QUICKBUILD_COST[i]))
        connection.send_chat('/build BUILDNUMBER')
    else:
        if connection.qb_index != None:
            connection.qb_building = False
            connection.qb_build_recorded = False
            connection.send_chat("No longer building.")
            return
        try:
            structure = int(structure)
            if structure >= len(QUICKBUILD_STRUCTURES) or structure < 0:
                raise ValueError()
        except ValueError:
            connection.send_chat('The structure that you entered is invalid.')
            return
        cost = QUICKBUILD_COST[structure]
        if connection.qb_points >= cost or connection.god:
            connection.qb_points -= cost
            connection.qb_index = structure
            connection.send_chat('The next block you place will build a %s.' 
                % QUICKBUILD_DESCRIPTION[structure])
            connection.qb_building = True
        else:
            connection.send_chat('You need %i more kills if you want to build #%i: %s.' 
                % (cost-connection.qb_points, structure, QUICKBUILD_DESCRIPTION[structure]))

add(build)

add(qbrecord)
add(qbsave)
add(qbclear)
add(qbundo)

add(qbprint)
add(qbrotate)
add(buildrecorded)

def apply_script(protocol, connection, config):
    cbc.set_protocol(protocol)
    
    # load config
    
    class BuildConnection(connection):
        def __init__(self, *arg, **kw):
            connection.__init__(self, *arg, **kw)
            self.quickbuild_allowed = True
            self.qb_index = None
            self.qb_points = 0
            self.qb_building = False
            
            self.qb_build_recorded = False
            self.qb_recording = 0
            self.qb_record_origin = None
            self.qb_record_dir = None
            self.qb_recorded = collections.OrderedDict()
        
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
        
        def on_block_build_attempt(self, x, y, z):
            if self.qb_building:
                self.qb_building = False
                color = self.color + (255,)
                if self.qb_build_recorded:
                    structure = rotate_all_dict_keys(EAST, self.get_direction(), self.qb_recorded)
                else:
                    structure = QUICKBUILD_STRUCTURES[self.qb_index]
                    structure = rotate_all(EAST, self.get_direction(), structure)
                    self.qb_index = None
                # structure is an iterator
                self.send_chat('Building structure.')
                cbc.add(self.quickbuild_generator((x, y, z), structure, color))
                return False
            elif self.qb_recording and self.qb_record_origin is None:
                self.qb_record_origin = (x, y, z)
                self.qb_record_dir = self.get_direction()
                return False
            return connection.on_block_build_attempt(self, x, y, z)
        
        def quickbuild_block_build(self, x, y, z):
            if self.qb_recording:
                if self.qb_record_origin is None:
                    self.qb_record_origin = (x, y, z)
                    self.qb_record_dir = self.get_direction()
                xyz = (x-self.qb_record_origin[0],
                       y-self.qb_record_origin[1],
                         self.qb_record_origin[2]-z)
                xyz = rotate(self.qb_record_dir, EAST, *xyz)
                self.qb_recorded[xyz] = self.color if self.qb_recording == 2 else None
        
        def quickbuild_generator(self, origin, structure, default_color):
            xo, yo, zo = origin
            map = self.protocol.map
            block_action = BlockAction()
            block_action.value = BUILD_BLOCK
            block_action.player_id = self.player_id
            for x, y, z in structure:
                x, y, z = x + xo, y + yo, z + zo
                if (x < 0 or x >= 512 or y < 0 or y >= 512 or z < 0 or z >= 62):
                    continue
                if map.get_solid(x, y, z):
                    continue
                self.on_block_build(x, y, z)
                block_action.x, block_action.y, block_action.z = x, y, z
                self.protocol.send_contained(block_action, save = True)
                map.set_point(x, y, z, default_color)
                yield 1, 0
    
    return protocol, BuildConnection