"""
teamchat_mute: make mute mute people in teamchat as well as global chat

topo 10/10/2012
"""
def apply_script(protocol, connection, config):
    class TeamMuteConnection(connection):
        def on_chat(self, value, is_global):
            if not is_global and self.mute:
                return False
            return connection.on_chat(self, value, is_global)
    return protocol, TeamMuteConnection
