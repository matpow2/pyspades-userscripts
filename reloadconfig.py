from commands import add, admin
import json

@admin
def reloadconfig(connection):
    new_config = {}
    try:
        new_config = json.load(open('config.txt', 'r'))
        if not isinstance(new_config, dict):
            raise ValueError('config.txt is not a mapping type')
    except ValueError, v:
        print 'Error reloading config:', v
        return 'Error reloading config. Check pyspades log for details.'
    connection.protocol.config.update(new_config)
    return 'Config reloaded!'

add(reloadconfig)

def apply_script(protocol, connection, config):
    return protocol, connection
