"""
Script tool for progressively applying a large number of block changes to the map.

Usage:
    # start
    generator = self.create_generator_function()
    handle = protocol.cbc_add(generator, update_interval, self.callback_function, *callback_args)
    # update_interval is the time (in seconds) between calls to `self.callback_function`
    
    # stop
    protocol.cbc_cancel(handle)

Callback receives these args:

    def callback_function(cbc_type, progress, total_elapsed_seconds, *callback_args):

The generator function should `yield <packets>, <progress>` for each unique packet sent to clients
Where packets is the number of packets sent this iteration, and progress is the current progress percentage

Maintainer: infogulch
"""

from twisted.internet.task import LoopingCall
import time

# the scripts list in config.txt needs to include THIS file BEFORE other files that depend on it

# cbc types
CBC_UPDATE, CBC_CANCELLED, CBC_FINISHED = range(3)

class CbcInfo:
    generator = None
    update_interval = 0.0
    callback = None
    callback_args = None
    last_update = time.time()
    start = time.time()
    progress = 0.0
    
    def __init__(self, generator, update_interval, callback, *callback_args):
        self.generator = generator
        self.update_interval = update_interval
        self.callback = callback
        self.callback_args = callback_args

def apply_script(protocol, connection, config):
    class CycleBlockCoiteratorProtocol(protocol):
        # cbc = Cycle Block Coiterator
        cbc_generators = None
        cbc_max_unique_packets = 30 # per 'cycle', each block op is at least 1
        cbc_max_packets = 300       # per 'cycle' cap for (unique packets * players)
        cbc_max_time = 0.03
        cbc_time_between_cycles = 0.06
        cbc_time_between_progress_updates = 10.0
        cbc_call = None
        cbc_running = False
        
        def __init__(self, *arg, **kw):
            protocol.__init__(self, *arg, **kw)
            self.cbc_generators = {}
        
        def cbc_add(self, generator, update = 10.0, callback = None, *args):
            info = CbcInfo(generator, update, callback, args)
            key = max(self.cbc_generators.keys() + [0]) + 1
            self.cbc_generators[key] = info
            if self.cbc_call is None:
                self.cbc_call = LoopingCall(self.cbc_cycle)
            if not self.cbc_running:
                self.cbc_running = True
                self.cbc_call.start(self.cbc_time_between_cycles, False)
            #this key lets you cancel in the middle later
            return key
        
        def cbc_cancel(key):
            if self.cbc_generators.has_key(key):
                info = self.cbc_generators[key]
                if not info.callback is None:
                    info.callback(CBC_CANCELLED, info.progress, time.time() - info.start, *info.callback_args)
                del self.cbc_generators[key]
        
        def cbc_cycle(self):
            sent_unique = sent_total = progress = 0
            current_key = None
            cycle_time = time.time()
            while len(self.cbc_generators) > 0:
                try:
                    for key, info in self.cbc_generators.iteritems():
                        if sent_unique > self.cbc_max_unique_packets:
                            return
                        if sent_total > self.cbc_max_packets:
                            return
                        if time.time() - cycle_time > self.cbc_max_time:
                            return
                        current_key = key
                        sent, progress = info.generator.next()
                        sent_unique += sent
                        sent_total  += sent * len(self.connections)
                        if (time.time() - info.last_update > info.update_interval):
                            info.last_update = time.time()
                            info.progress = progress
                            if not info.callback is None:
                                info.callback(CBC_UPDATE, progress, time.time() - info.start, *info.callback_args)
                except (StopIteration):
                    info = self.cbc_generators[current_key]
                    if not info.callback is None:
                        info.callback(CBC_FINISHED, progress, time.time() - info.start, *info.callback_args)
                    del self.cbc_generators[current_key]
            if len(self.cbc_generators) == 0:
                self.cbc_call.stop()
                self.cbc_running = False
        
        def on_map_change(self, map):
            if self.cbc_generators is not None:
                for key in self.cbc_generators:
                    self.cbc_cancel(key)
            protocol.on_map_change(self, map)
        
        def on_map_leave(self):
            if self.cbc_generators is not None:
                for key in self.cbc_generators:
                    self.cbc_cancel(key)
            protocol.on_map_leave(self)
    
    return CycleBlockCoiteratorProtocol, connection