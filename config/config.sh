#!/bin/bash
#
# Functions to retrieve values from config.
#

CONFIG_FILE='config/config-update.yaml'

function get_config_value {
    INDEX=
    while [ -n "$1" ]; do
        VAR=$(sed s/\'/\\\\\'/g <<< "$1")
        INDEX="$INDEX['$VAR']"
        shift
    done

    python3 -c "
import yaml
with open('$CONFIG_FILE') as f:
    print(yaml.load(f)$INDEX)
    "
}

function get_config_list {
    INDEX=
    while [ -n "$1" ]; do
        VAR=$(sed s/\'/\\\\\'/g <<< "$1")
        INDEX="$INDEX['$VAR']"
        shift
    done

    python3 -c "
import yaml
with open('$CONFIG_FILE') as f:
    print(' '.join(yaml.load(f)$INDEX))
    "
}

function get_config_keys {
    INDEX=
    while [ -n "$1" ]; do
        VAR=$(sed s/\'/\\\\\'/g <<< "$1")
        INDEX="$INDEX['$VAR']"
        shift
    done

    python3 -c "
import yaml
with open('$CONFIG_FILE') as f:
    print(' '.join(yaml.load(f)$INDEX.keys()))
    "
}
