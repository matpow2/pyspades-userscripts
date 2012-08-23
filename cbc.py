"""
Script tool for progressively applying a large number of block changes to the map.

Usage:
    # At the top of the file
    import cbc
    
    # in your apply_script() function
    
    apply_script(protocol, connection, config)
        protocol, connection = cbc.apply_script(protocol, connection, config)
    
    # start
    generator = self.create_generator_function()
    
    handle = self.protocol.cbc_add(generator)
    # or
    handle = self.protocol.cbc_add(generator, update_interval, self.callback_function, *callback_args)
    
    # update_interval is the time (in seconds) between calls to `self.callback_function`
    
    # stop
    self.protocol.cbc_cancel(handle)

Callback receives these args:

    def callback_function(self, cbc_type, progress, total_elapsed_seconds, *callback_args):

The generator function should `yield <packets>, <progress>` for each unique packet sent to clients
Where packets is the number of packets sent this iteration, and progress is the current progress percentage

Author: infogulch
"""

from twisted.internet.task import LoopingCall
import time
import random

class _CbcInfo:
    generator = None
    update_interval = 0.0
    callback = None
    callback_args = None
    last_update = time.time()
    start = time.time()
    progress = 0.0
    
    def __init__(self, generator, update_interval, callback, callback_args):
        self.generator = generator
        self.update_interval = update_interval
        self.callback = callback
        self.callback_args = callback_args

#note: client crashes when this goes over ~50
class ServerPlayer(object):
    server_players = set()
    
    def __init__(self):
        id = 33
        while id in ServerPlayer.server_players:
            id += 1
        self.player_id = id
        ServerPlayer.server_players.add(id)
    
    def __del__(self):
        ServerPlayer.server_players.discard(self.player_id)

TIME_BETWEEN_CYCLES = 0.06
MAX_UNIQUE_PACKETS = 30 # per 'cycle', each block op is at least 1
MAX_PACKETS = 300       # per 'cycle' cap for (unique packets * players)
MAX_TIME = 0.03         # max time each cycle takes

def apply_script(protocol, connection, config):
    if hasattr(protocol, 'cbc_add'):
        return protocol, connection
    
    class CycleBlockCoiteratorProtocol(protocol):
        CBC_UPDATE, CBC_CANCELLED, CBC_FINISHED = range(3)
        
        def __init__(self, *args, **kwargs):
            protocol.__init__(self, *args, **kwargs)
            
            self._cbc_running = False
            self._cbc_generators = {}
            self._cbc_call = LoopingCall(self._cbc_cycle)
        
        def cbc_add(self, generator, update_time = 10.0, callback = None, *args):
            info = _CbcInfo(generator, update_time, callback, args)
            handle = max(self._cbc_generators.keys() + [0]) + 1
            self._cbc_generators[handle] = info
            if not self._cbc_running:
                self._cbc_running = True
                self._cbc_call.start(TIME_BETWEEN_CYCLES, False)
            #this handle lets you cancel in the middle later
            return handle
        
        def cbc_cancel(self, handle):
            if self._cbc_generators.has_key(handle):
                info = self._cbc_generators[handle]
                if info.callback is not None:
                    info.callback(CANCELLED, info.progress, time.time() - info.start, *info.callback_args)
                del self._cbc_generators[handle]
        
        def _cbc_cycle(self):
            sent_unique = sent_total = progress = 0
            current_handle = None
            cycle_time = time.time()
            while self._cbc_generators:
                try:
                    for handle, info in self._cbc_generators.iteritems():
                        if sent_unique > MAX_UNIQUE_PACKETS:
                            return
                        if sent_total > MAX_PACKETS:
                            return
                        if time.time() - cycle_time > MAX_TIME:
                            return
                        current_handle = handle
                        sent, progress = info.generator.next()
                        sent_unique += sent
                        sent_total  += sent * len(self.players)
                        if (time.time() - info.last_update > info.update_interval):
                            info.last_update = time.time()
                            info.progress = progress
                            if not info.callback is None:
                                info.callback(self.CBC_UPDATE, progress, time.time() - info.start, *info.callback_args)
                except StopIteration:
                    info = self._cbc_generators[current_handle]
                    if info.callback is not None:
                        info.callback(self.CBC_FINISHED, progress, time.time() - info.start, *info.callback_args)
                    del self._cbc_generators[current_handle]
            else:
                self._cbc_call.stop()
                self._cbc_running = False
        
        def on_map_change(self, map):
            if hasattr(self, '_cbc_generators'):
                for handle in self._cbc_generators.keys():
                    self.cbc_cancel(handle)
            protocol.on_map_change(self, map)
        
        def on_map_leave(self):
            if hasattr(self, '_cbc_generators'):
                for handle in self._cbc_generators.keys():
                    self.cbc_cancel(handle)
            protocol.on_map_leave(self)
    
    return CycleBlockCoiteratorProtocol, connection