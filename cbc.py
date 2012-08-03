"""
Script tool for progressively applying a large number of block changes to the map.

Usage:
    # At the top of the file
    import cbc
    
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

MAX_UNIQUE_PACKETS = 30 # per 'cycle', each block op is at least 1
MAX_PACKETS = 300       # per 'cycle' cap for (unique packets * players)
MAX_TIME = 0.03
TIME_BETWEEN_CYCLES = 0.06

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

_running = False
_generators = {}
_protocol = None
_call = None

UPDATE, CANCELLED, FINISHED = range(3)

def add(generator, update_time = 10.0, callback = None, *args):
    global _running, _generators, _protocol, _call
    if _protocol is None:
        raise ValueError()
    info = _CbcInfo(generator, update_time, callback, args)
    handle = max(_generators.keys() + [0]) + 1
    _generators[handle] = info
    if not _running:
        _running = True
        _call.start(TIME_BETWEEN_CYCLES, False)
    #this handle lets you cancel in the middle later
    return handle

def cancel(handle):
    global _running, _generators, _protocol, _call
    if _generators.has_key(handle):
        info = _generators[handle]
        if info.callback is not None:
            info.callback(CANCELLED, info.progress, time.time() - info.start, *info.callback_args)
        del _generators[handle]

def _cycle():
    global _running, _generators, _protocol, _call
    sent_unique = sent_total = progress = 0
    current_handle = None
    cycle_time = time.time()
    while len(_generators) > 0:
        try:
            for handle, info in _generators.iteritems():
                if sent_unique > MAX_UNIQUE_PACKETS:
                    return
                if sent_total > MAX_PACKETS:
                    return
                if time.time() - cycle_time > MAX_TIME:
                    return
                current_handle = handle
                sent, progress = info.generator.next()
                sent_unique += sent
                sent_total  += sent * len(_protocol.players)
                if (time.time() - info.last_update > info.update_interval):
                    info.last_update = time.time()
                    info.progress = progress
                    if not info.callback is None:
                        info.callback(UPDATE, progress, time.time() - info.start, *info.callback_args)
        except (StopIteration):
            info = _generators[current_handle]
            if not info.callback is None:
                info.callback(FINISHED, progress, time.time() - info.start, *info.callback_args)
            del _generators[current_handle]
    if len(_generators) == 0:
        _call.stop()
        _running = False

_call = LoopingCall(_cycle)

def set_protocol(protocol):
    global _running, _generators, _protocol, _call
    # manually override these functions instead of inhertiting
    # allows this script to be completely separate, and not included in config.txt scripts
    # slightly more work for script authors, slightly less work for server hosts
    if set_protocol.has_run:
        return
    
    set_protocol.has_run = True
    
    #save the current ones
    saved_on_map_change = protocol.on_map_change
    saved_on_map_leave  = protocol.on_map_leave
    
    def on_map_change(self, map):
        global _protocol
        if _protocol is None:
            _protocol = self
        for handle in _generators.keys():
            cancel(handle)
        saved_on_map_change(self, map)
    
    def on_map_leave(self):
        global _protocol
        if _protocol is None:
            _protocol = self
        for handle in _generators.keys():
            cancel(handle)
        saved_on_map_leave(self)
    
    #overwrite them
    protocol.on_map_change = on_map_change
    protocol.on_map_leave  = on_map_leave

set_protocol.has_run = False

# little snippet to prevent people from including this script in the config.txt anymore
def apply_script(*a):
    raise NotImplementedError('"cbc" should not be included in config.txt!')