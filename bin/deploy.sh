#!/bin/bash
#
# Deploys the code to a specified server.
#

function usage {
    echo "Usage: $0 <server> [options]" >&2
    echo >&2
    echo 'Options:'
    echo '--code        Send UI and API code to the server' >&2
    echo '--data        Send data to the server' >&2
    echo '--tiles       Send climate tiles to the server' >&2
    echo '--map-tiles   Send map tiles to the server' >&2
    echo '--geonames    Send geonames to the server' >&2
    echo '--build       Run javascript build' >&2
    exit 1
}

if [ -z "$1" ]; then
    usage
fi

SERVER="$1"
shift

while [ -n "$1" ]; do
    case $1 in
        --code)
            COPY_CODE=1
            ;;
        --data)
            COPY_DATA=1
            ;;
        --tiles)
            COPY_TILES=1
            ;;
        --map-tiles)
            COPY_MAP_TILES=1
            ;;
        --geonames)
            COPY_GEONAMES=1
            ;;
        --build)
            DO_BUILD=1
            ;;
        *)
            usage
            ;;
    esac
    shift
done

REPO=$(dirname "$0")/..
REPO_NAME=$(basename $(realpath "$REPO"))
DESTINATION="$SERVER:$REPO_NAME"

source config/config.sh config/config.yaml

DB_NAME=$(get_config_value database name) || exit 1

RSYNC='rsync --delete-delay -ipRru'

function copy_tables {
    mysqldump $DB_NAME $@ | ssh "$SERVER" mysql $DB_NAME
}

cd $REPO

if [ $COPY_DATA ]; then
    $RSYNC --exclude=data/*-calibrated-* data "$DESTINATION" || exit 1
    if [ $(read -p 'Copy database tables? [y/n]' A && echo $A) == 'y' ]; then
        copy_tables data_sources datasets measurements units || exit 1
    fi
fi

if [ $COPY_TILES ]; then
    $RSYNC tiles "$DESTINATION" || exit 1
fi

if [ $COPY_MAP_TILES ]; then
    $RSYNC public/map-tiles "$DESTINATION" || exit 1
fi

if [ $COPY_GEONAMES ]; then
    copy_tables countries provinces geonames alternate_names || exit 1
fi

if [ $COPY_CODE ]; then
    $RSYNC --exclude=__pycache__ src "$DESTINATION" || exit 1
    $RSYNC --exclude=public/*bundle.js public/*.* "$DESTINATION" || exit 1
    $RSYNC --exclude=images/*.xcf images "$DESTINATION" || exit 1
    $RSYNC sql "$DESTINATION" || exit 1
    $RSYNC package.json webpack.config.js "$DESTINATION" || exit 1
    $RSYNC config/config.yaml.example "$DESTINATION" || exit 1
    $RSYNC config/config.json.example "$DESTINATION" || exit 1
fi

if [ $DO_BUILD ]; then
    ssh "$SERVER" "cd $REPO_NAME && npm update && rm public/*.bundle.js && npm run build"
fi
