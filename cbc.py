"""
Script tool for progressively applying a large number of block changes to the map.

Usage:
    # At the top of the file
    from cbc import cbc
    
    #in your apply_script() function
    apply_script(protocol, connection, config)
        cbc.set_protocol(protocol)
    
    # start
    generator = self.create_generator_function()
    handle = cbc.add(generator, update_interval, self.callback_function, *callback_args)
    # update_interval is the time (in seconds) between calls to `self.callback_function`
    
    # stop
    cbc.cancel(handle)

Callback receives these args:

    def callback_function(self, cbc_type, progress, total_elapsed_seconds, *callback_args):

The generator function should `yield <packets>, <progress>` for each unique packet sent to clients
Where packets is the number of packets sent this iteration, and progress is the current progress percentage

Author: infogulch
"""

from twisted.internet.task import LoopingCall
import time
import random

_MAX_UNIQUE_PACKETS = 30     # per 'cycle', each block op is at least 1
# _MAX_PACKETS = 300           # per 'cycle' cap for (unique packets * players)
_MAX_TIME = 0.03
_TIME_BETWEEN_CYCLES = 0.06

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

class _CycleBlockCoiterator:
    _running = False
    _generators = {}
    _protocol = None
    _call = None
    
    UPDATE, CANCELLED, FINISHED = range(3)
    
    def __init__(self):
        self._call = LoopingCall(self._cycle)
    
    def set_protocol(self, protocol):
        # manually override these functions instead of inhertiting
        # allows this script to be completely separate, and not included in config.txt scripts
        if self._protocol is None and not protocol is None:
            self._protocol = protocol
            
            #save the current ones
            self.protocol_on_map_change = protocol.on_map_change
            self.protocol_on_map_leave  = protocol.on_map_leave
            
            #overwrite them
            protocol.on_map_change = self._on_map_change
            protocol.on_map_leave  = self._on_map_leave
    
    def add(self, generator, update_time = 10.0, callback = None, *args):
        if self._protocol is None:
            raise ValueError()
        info = _CbcInfo(generator, update_time, callback, args)
        handle = max(self._generators.keys() + [0]) + 1
        self._generators[handle] = info
        if not self._running:
            self._running = True
            self._call.start(_TIME_BETWEEN_CYCLES, False)
        #this handle lets you cancel in the middle later
        return handle
    
    def cancel(self, handle):
        if self._generators.has_key(handle):
            info = self._generators[handle]
            if not info.callback is None:
                info.callback(self.CANCELLED, info.progress, time.time() - info.start, *info.callback_args)
            del self._generators[handle]
    
    def _cycle(self):
        sent_unique = sent_total = progress = 0
        current_handle = None
        cycle_time = time.time()
        while len(self._generators) > 0:
            try:
                for handle, info in self._generators.iteritems():
                    if sent_unique > _MAX_UNIQUE_PACKETS:
                        return
                    # if sent_total > _MAX_PACKETS:
                        # return
                    if time.time() - cycle_time > _MAX_TIME:
                        return
                    current_handle = handle
                    sent, progress = info.generator.next()
                    sent_unique += sent
                    # sent_total  += sent * len(self._protocol.connections) #can't get the property anymore
                    if (time.time() - info.last_update > info.update_interval):
                        info.last_update = time.time()
                        info.progress = progress
                        if not info.callback is None:
                            info.callback(self.UPDATE, progress, time.time() - info.start, *info.callback_args)
            except (StopIteration):
                info = self._generators[current_handle]
                if not info.callback is None:
                    info.callback(self.FINISHED, progress, time.time() - info.start, *info.callback_args)
                del self._generators[current_handle]
        if len(self._generators) == 0:
            self._call.stop()
            self._running = False
    
    def _on_map_change(self, pself, map):
        for handle in self._generators.keys():
            self.cancel(handle)
        self.protocol_on_map_change(pself, map)
    
    def _on_map_leave(self, pself):
        for handle in self._generators.keys():
            self.cancel(handle)
        self.protocol_on_map_leave(pself)

### shared instance ###
cbc = _CycleBlockCoiterator()
