from pyspades.contained import BlockAction
from pyspades.constants import *
from itertools import product, chain
import cbc

# this file must be in the /scripts folder, but it is NOT included in config.txt

def clear_solid_generator(protocol, x1, y1, z1, x2, y2, z2, god = False, destroy = True):
    block_action = BlockAction()
    block_action.value = DESTROY_BLOCK
    splayer = cbc.ServerPlayer()
    block_action.player_id = splayer.player_id
    map = protocol.map
    check_protected = hasattr(protocol, 'protected')
    x1, x2 = sorted((x1 , x2))
    y1, y2 = sorted((y1 , y2))
    z1, z2 = sorted((z1 , z2))
    clear = map.destroy_point if destroy else map.remove_point
    get_solid = map.get_solid
    for x, y, z in product( xrange(x1, x2+1)
                          , xrange(y1, y2+1)
                          , xrange(z1, z2+1)):
        packets = 0
        if get_solid(x, y, z) and (god or 
                    not (check_protected and protocol.is_protected(x, y, z)) #not protected
                and not (protocol.god_blocks is not None and (x, y, z) in protocol.god_blocks)): #not a god block
            block_action.x = x
            block_action.y = y
            block_action.z = z
            protocol.send_contained(block_action, save = True)
            clear(x, y, z)
            packets = 1
        yield packets, 0

def clear_solid(protocol, x1, y1, z1, x2, y2, z2, god = False):
    if (x1 < 0 or x1 >= 512 or y1 < 0 or y1 >= 512 or z1 < 0 or z1 > 64 or
        x2 < 0 or x2 >= 512 or y2 < 0 or y2 >= 512 or z2 < 0 or z2 > 64):
        raise ValueError('Invalid coordinates: (%i, %i, %i):(%i, %i, %i)' % (x1, y1, z1, x2, y2, z2))
    protocol.cbc_add(clear_solid_generator(protocol, x1, y1, z1, x2, y2, z2, god))

def clear(protocol, x1, y1, z1, x2, y2, z2, god = False):
    x1, x2 = sorted((x1, x2))
    y1, y2 = sorted((y1, y2))
    z1, z2 = sorted((z1, z2))
    lst = (
        clear_solid_generator(protocol, x1, y1, z2, x2, y2, z2, god, False)
      , clear_solid_generator(protocol, x1, y1, z1, x1, y2, z2, god, False)
      , clear_solid_generator(protocol, x2, y1, z1, x2, y2, z2, god, False)
      , clear_solid_generator(protocol, x1, y1, z1, x2, y1, z2, god, False)
      , clear_solid_generator(protocol, x1, y2, z1, x2, y2, z2, god, False)
      , clear_solid_generator(protocol, x1, y1, z1, x2, y2, z1, god, False)
      , clear_solid_generator(protocol, x1, y1, z1, x2, y2, z2, god, True))
    
    protocol.cbc_add(chain.from_iterable(lst))
