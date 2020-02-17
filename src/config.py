#!/usr/bin/env python3
#
# Reads the configuration file.
#

import yaml
import os

CONFIG_DIR_NAME = 'config'
CONFIG_FILENAME = 'config.yaml'

def _load():
    '''
    Loads the config variables
    '''
    config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), CONFIG_DIR_NAME)
    config_file = os.path.join(config_dir, CONFIG_FILENAME)

    with open(config_file, 'r') as f:
        yaml_data = yaml.load(f)

    return yaml_data

class _Object():
    '''
    Basic object to be able to export config variables as "config.database.name", etc.
    '''
    pass

# Export config variables as module attributes to access them as "config.database.name", etc.

_yaml_data = _load()

database = _Object()
database.name = _yaml_data['database']['name']
database.host = _yaml_data['database']['host']
database.user = _yaml_data['database']['user']
database.password = _yaml_data['database']['password']

del _yaml_data
