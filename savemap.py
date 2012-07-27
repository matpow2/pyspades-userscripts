"""
Saves current map on shutdown (and optionally loads it again on startup)

/savemap manually saves the map in the format of  <mapname>.manual.<time>.vxl

new config.txt options: 
    "autosave_interval" : <minutes, 0 to disable>
    "autosave_max" : <maximum autosaves, old ones are deleted>

Maintainer: mat^2
(modified by infoguluch)
"""

import commands
from twisted.internet import reactor
from pyspades.vxl import VXLData
from twisted.internet.task import LoopingCall
from time import gmtime, strftime
from commands import add, admin
from glob import glob
import os

def get_name(map, type = 'saved', time = False):
    return './maps/%s.%s%s.vxl' % (map.rot_info.name, type, strftime(".%Y%m%d.%H%M%S", gmtime()) if time else '')

def save_map(map, name):
    open(name, 'wb').write(map.generate())

@admin
def savemap(connection):
    connection.send_chat('Saving map...')
    save_map(connection.protocol.map, get_name(connection.protocol.map_info, 'manual', True))
    return 'Map saved'
add(savemap)

def apply_script(protocol, connection, config):
    class MapSaveProtocol(protocol):
        def __init__(self, *arg, **kw):
            protocol.__init__(self, *arg, **kw)
            reactor.addSystemEventTrigger('before', 'shutdown', self.save_map)
            self.autosave_interval = config.get('autosave_interval', 0.0)
            if self.autosave_interval:
                self.autosave_max  = int(config.get('autosave_max', 0))
                self.autosave_loop = LoopingCall(self.save_map, 'autosave', True, self.autosave_max)
                self.autosave_loop.start(self.autosave_interval * 60.0, False)
        
        def get_map(self, rot_info):
            map = protocol.get_map(self, rot_info)
            if config.get('load_saved_map', False):
                cached_path = get_name(map)
                if os.path.isfile(cached_path):
                    map.data = VXLData(open(cached_path, 'rb'))
            return map
        
        def save_map(self, type = 'saved', time = False, max = 0):
            name = get_name(self.map_info, type, time)
            save_map(self.map, name)
            if max > 0 and time: # delete old files past max count
                for path in sorted(glob(name[:-19] + '*' + name[-4:]))[::-1][max:]:
                    os.remove(path)

    return MapSaveProtocol, connection