from commands import add, admin
from math import floor, atan2
from pyspades.constants import *
from pyspades.contained import BlockAction

QUICKBUILD_WALL = ((0, 0, 0), (-1, 0, 0), (-1, 0, 1), (-2, 0, 0), (-2, 0, 1), 
                   (-3, 0, 0), (-3, 0, 1), (0, 0, 1), (1, 0, 0), (1, 0, 1),
                   (2, 0, 0), (2, 0, 1), (3, 0, 0), (3, 0, 1), (-3, -1, 0), (-3, -1, 1), (-3, -2, 0),
                   (-3, -2, 1),(3, -1, 0), (3, -1, 1), (3, -2, 0), (3, -2, 1))
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

# Don't touch these values
EAST = 0
SOUTH = 1
WEST = 2
NORTH = 3
UPDATE_RATE = 1.0

# Use these commands to create quickbuild structures.
@admin
def qbrecord(connection):
    if connection.quickbuild_mode == QB_RECORDING:
        connection.quickbuild_mode = QB_DISABLED
        qbclear(connection)
        connection.send_chat('You are no longer recording.')
    else:
        connection.quickbuild_mode = QB_RECORDING
        connection.send_chat('You are now recording.')

@admin
def qbprint(connection):
    print connection.quickbuild_recorded
    connection.send_chat('Printed quickbuild data.')

@admin
def qbclear(connection):
    connection.quickbuild_recorded = []
    connection.quickbuild_record_origin = None

@admin
def qbundo(connection):
    if len(connection.quickbuild_recorded):
        connection.quickbuild_recorded.pop()

def build(connection, structure = None):
    if not connection.quickbuild_allowed:
        connection.send_chat('You are not allowed to build')
        return
    if structure == None:
        connection.quickbuild_mode = QB_DISABLED
        connection.quickbuild_index = None
        for i in xrange(len(QUICKBUILD_STRUCTURES)):
            connection.send_chat('%i: Build a %s. Requires %i kills.' 
                % (i, QUICKBUILD_DESCRIPTION[i], QUICKBUILD_COST[i]))
        connection.send_chat('/build BUILDNUMBER')
    else:
        if connection.quickbuid_index != None:
            connection.send_chat("You're already building #%i: %s." 
                % (connection.quickbuid_index, QUICKBUILD_DESCRIPTION[connection.quickbuid_index]))
            return
        try:
            structure = int(structure)
            if structure >= len(QUICKBUILD_STRUCTURES) or structure < 0:
                raise ValueError()
        except ValueError:
            connection.send_chat('The structure that you entered is invalid.')
            return
        cost = QUICKBUILD_COST[structure]
        if connection.quickbuild_points >= cost:
            connection.quickbuild_points -= cost
            connection.quickbuid_index = structure
            connection.send_chat('The next block you place will build a %s.' 
                % QUICKBUILD_DESCRIPTION[structure])
            connection.quickbuild_mode = QB_ENABLED
        else:
            connection.send_chat('You need %i more kills if you want to build #%i: %s.' 
                % (cost-connection.quickbuild_points, structure, QUICKBUILD_DESCRIPTION[structure]))

def b(connection, structure = None):
    build(connection, structure)

add(build)
add(b)
add(qbrecord)
add(qbprint)
add(qbclear)
add(qbundo)

QB_DISABLED, QB_ENABLED, QB_RECORDING = xrange(3)

def apply_script(protocol, connection, config):
    class BuildConnection(connection):
        def get_direction(self):
            orientation = self.world_object.orientation
            angle = atan2(orientation.y, orientation.x)
            if angle < 0:
                angle += 6.283185307179586476925286766559
            # Convert to units of quadrents
            angle *= 0.63661977236758134307553505349006
            angle = round(angle)
            if angle == 4:
                angle = 0
            return angle
        
        def on_join(self):
            self.quickbuild_allowed = True
            self.quickbuid_index = None
            self.quickbuild_points = 0
            self.quickbuild_mode = QB_DISABLED
            self.quickbuild_record_origin = None
            self.quickbuild_recorded = []
            return connection.on_join(self)
        
        def on_kill(self, killer, type, grenade):
            ret = connection.on_kill(self, killer, type, grenade)
            if ret is None:
                if killer is not None and self.team is not killer.team and self != killer:
                    killer.quickbuild_points += 1
            return ret
        
        def on_line_build(self, points):
            for x, y, z in points:
                self.quickbuild_block_build(x, y, z)
            return connection.on_line_build(self, points)
        
        def on_block_build(self, x, y, z):
            self.quickbuild_block_build(x, y, z)
            return connection.on_block_build(self, x, y, z)
        
        def quickbuild_block_build(self, x, y, z):
            if self.quickbuild_mode == QB_RECORDING:
                if self.quickbuild_record_origin == None:
                    self.quickbuild_record_origin = (x, y, z)
                    self.quickbuild_recorded.append((0, 0, 0))
                else:
                    self.quickbuild_recorded.append((x-self.quickbuild_record_origin[0],
                                                 self.quickbuild_record_origin[1]-y,
                                                 self.quickbuild_record_origin[2]-z))
            elif self.quickbuild_mode == QB_ENABLED:
                self.quickbuild_mode = QB_DISABLED
                color = self.color + (255,)
                facing = self.get_direction()
                structure = QUICKBUILD_STRUCTURES[self.quickbuid_index]
                self.quickbuid_index = None
                self.protocol.cbc_add(self.quickbuild_generator((x, y, z), structure, facing, color))
        
        def quickbuild_generator(self, origin, structure, facing, color):
            x, y, z = origin
            map = self.protocol.map
            block_action = BlockAction()
            block_action.value = BUILD_BLOCK
            block_action.player_id = self.player_id
            for bx, by, bz in structure:
                if facing == NORTH:
                    bx, by = bx, -by
                elif facing == WEST:
                    bx, by = -by, -bx
                elif facing == SOUTH:
                    bx, by = -bx, by
                elif facing == EAST:
                    bx, by = by, bx
                bx, by, bz = x+bx, y+by, z-bz
                if (bx < 0 or bx >= 512 or by < 0 or by >= 512 or bz < 0 or
                    bz >= 62):
                    continue
                if map.get_solid(bx, by, bz):
                    continue
                block_action.x = bx
                block_action.y = by
                block_action.z = bz
                self.protocol.send_contained(block_action, save = True)
                map.set_point(bx, by, bz, color)
            
    
    return protocol, BuildConnection