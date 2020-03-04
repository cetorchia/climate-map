#!/bin/bash
#
# Deploys the code to a specified server.
#

if [ -z "$1" -o -n "$3" ]; then
    echo "Usage: $0 <server> [--data|--tiles|--config]" >&2
fi

if [ "$2" == "--data" ]; then
    COPY_DATA=1
elif [ "$2" == "--tiles" ]; then
    COPY_TILES=1
elif [ "$2" == "--config" ]; then
    COPY_CONFIG=1
fi

SERVER="$1"
REPO=$(dirname "$0")/..
REPO_NAME=$(basename $(realpath "$REPO"))
DESTINATION="$SERVER:$REPO_NAME"

cd $REPO

if [ $COPY_DATA ]; then
    rsync -pRr --exclude=*-calibrated-* --del data "$DESTINATION"
elif [ $COPY_TILES ]; then
    rsync -pRr --del public/tiles "$DESTINATION"
elif [ $COPY_CONFIG ]; then
    rsync -pRr --del config/config.yaml.example "$DESTINATION"
else
    rsync -pRr --del --exclude=__pycache__ src "$DESTINATION"
    rsync -pRr --del --exclude=*bundle.js public/*.* "$DESTINATION"
    rsync -pRr --del sql "$DESTINATION"
    rsync -pR package.json webpack.config.js "$DESTINATION"
fi
