"""
MeleeRotation
Melee round every N rounds.

Requires melee.py to be loaded.

ISSUES:
    1. The first N rounds are melee unless the mode is manually unset
       when meleerotation is below melee in config.txt
    2. Players must return to their tentthings once melee mode is off
       to be able to shoot.
"""

ROTATE_EVERY = 3

def apply_script(protocol, connection, config):
    class MeleeRotationProtocol(protocol):
        def __init__(self, *arg, **kw):
            self.melee_mode = False
            self.round      = 1
            protocol.__init__(self, *arg, **kw)
    
    class MeleeRotationConnection(connection):
        def on_flag_capture(self):
            protocol = self.protocol
            
            self.has_intel = False
            protocol.round += 1
            
            if protocol.round % ROTATE_EVERY == 0:
                protocol.melee_mode = True
                protocol.send_chat("This is a melee round!")
            elif protocol.round % ROTATE_EVERY == 1:
                protocol.melee_mode = False
                protocol.send_chat("The melee round is over.")

            return connection.on_flag_capture(self)
        
    return MeleeRotationProtocol, MeleeRotationConnection
