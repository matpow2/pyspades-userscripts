"""
streak.py

for those who don't want to bother with the (currently broken) airstrike script
but still want the refills it gives and an easy framework for adding more
complicated stuff

maintainer: topo
"""

STREAK_REQUIREMENT = 8

def apply_script(protocol, connection, config):
    class StreakConnection(connection):
        last_streak = None
        
        def add_score(self, score):
            connection.add_score(self, score)
            if (self.streak % STREAK_REQUIREMENT == 0
            and self.streak != self.last_streak):
                self.refill()
                self.last_streak = self.streak

        def on_kill(self, killer, type, grenade):
            self.last_streak = None
            connection.on_kill(self, killer, type, grenade)

    return protocol, StreakConnection
