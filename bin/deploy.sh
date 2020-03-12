#!/bin/bash
#
# Deploys the code to a specified server.
#

if [ -z "$1" -o -n "$3" ]; then
    echo "Usage: $0 <server> [--data|--tiles|--config]" >&2
    exit 1
fi

if [ "$2" == "--data" ]; then
    COPY_DATA=1
elif [ "$2" == "--tiles" ]; then
    COPY_TILES=1
elif [ "$2" == "--config" ]; then
    COPY_CONFIG=1
elif [ "$2" == "--build" ]; then
    DO_BUILD=1
fi

SERVER="$1"
REPO=$(dirname "$0")/..
REPO_NAME=$(basename $(realpath "$REPO"))
DESTINATION="$SERVER:$REPO_NAME"

cd $REPO

if [ $COPY_DATA ]; then
    rsync -pRru --exclude=*-calibrated-* --del data "$DESTINATION"
elif [ $COPY_TILES ]; then
    rsync -pRru --del public/tiles "$DESTINATION"
elif [ $COPY_CONFIG ]; then
    rsync -pRru --del config/config.yaml.example "$DESTINATION"
    rsync -pRru --del config/config.json.example "$DESTINATION"
else
    rsync -pRru --del --exclude=__pycache__ src "$DESTINATION" || exit 1
    rsync -pRru --del --exclude=*bundle.js public/*.* "$DESTINATION" || exit 1
    rsync -pRru --del sql "$DESTINATION" || exit 1
    rsync -pRu package.json webpack.config.js "$DESTINATION" || exit 1
fi

if [ $DO_BUILD ]; then
    ssh $SERVER "cd $REPO_NAME && npm update && npm run build"
fi
