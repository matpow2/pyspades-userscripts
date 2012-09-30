"""
Make gradient lines!

/gradient r g b r g b

alias: /gr

Author: infogulch
"""

from pyspades.common import make_color
from pyspades.contained import BlockAction, SetColor
from pyspades.constants import *
from commands import add, alias

import cbc

@alias('gr')
def gradient(connection, *colors):
    if len(colors) != 6:
        if not connection.gradient_colors:
            return 'Usage: /gradient r g b r g b, OR choose from & to colors with /grf /grt'
        if not connection.gradient_enabled:
            connection.gradient_enabled = True
            return 'Gradient enabled. Colors are: (%i, %i, %i) (%i, %i, %i)' % (
                connection.gradient_colors[0] + connection.gradient_colors[1])
        else:
            connection.gradient_enabled = False
            return 'No longer making gradients.'
    try:
        colors = tuple(int(c) for c in colors)
        connection.gradient_colors = colors[:3], colors[3:]
        connection.gradient_enabled = True
        return 'The next line you build will create a gradient from (%i,%i,%i) to (%i,%i,%i).' % colors
    except ValueError:
        return 'All args must be integers.'

@alias('grf')
def gradientfrom(connection):
    if not connection.gradient_colors:
        connection.gradient_colors = [(0,0,0), (0,0,0)]
    connection.gradient_colors[0] = connection.color
    return 'Gradient from color is now: (%i %i %i)' % connection.color

@alias('grt')
def gradientto(connection):
    if not connection.gradient_colors:
        connection.gradient_colors = [(0,0,0), (0,0,0)]
    connection.gradient_colors[1] = connection.color
    return 'Gradient to color is now: (%i %i %i)' % connection.color

add(gradient)
add(gradientfrom)
add(gradientto)

def build_gradient_line(protocol, colors, points):
    sp = cbc.ServerPlayer()
    
    block_action = BlockAction()
    block_action.player_id = sp.player_id
    block_action.value = BUILD_BLOCK
    
    set_color = SetColor()
    set_color.player_id = sp.player_id
    
    color_range = zip(*colors)
    
    lp = len(points) - 1
    map = protocol.map
    for i in xrange(len(points)):
        if lp:
            pct = 1 - (i+0.0) / lp, (i+0.0) / lp
        else:
            pct = (1,0)
        
        color = tuple(int(round(sum(c*p for c,p in zip(crng, pct)))) for crng in color_range)
        
        map.set_point(*points[i], color = color)
        
        set_color.value = make_color(*color)
        protocol.send_contained(set_color, save = True)
        
        block_action.x, block_action.y, block_action.z = points[i]
        protocol.send_contained(block_action, save = True)

def apply_script(protocol, connection, config):
    class GradientConnection(connection):
        def __init__(self, *args, **kwargs):
            connection.__init__(self, *args, **kwargs)
            self.gradient_colors = []
            self.gradient_enabled = False
        
        def on_line_build_attempt(self, points):
            if connection.on_line_build_attempt(self, points) == False:
                return False
            if self.gradient_enabled:
                build_gradient_line(self.protocol, self.gradient_colors, points)
                return False
    
    return protocol, GradientConnection