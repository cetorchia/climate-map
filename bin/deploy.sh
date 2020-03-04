#!/bin/bash
#
# Deploys the code to a specified server.
#

if [ -z "$1" ]; then
    echo "Usage: $0 <server> [--data]" >&2
fi

if [ "$2" == "--data" ]; then
    COPY_DATA=1
fi

SERVER="$1"
REPO=$(dirname "$0")/..
REPO_NAME=$(basename $(realpath "$REPO"))
DESTINATION="$SERVER:$REPO_NAME"

cd $REPO
rsync -pRr --del --exclude=__pycache__ src "$DESTINATION"
rsync -pRr --del --exclude=*bundle.js public/*.* "$DESTINATION"
rsync -pRr --del sql "$DESTINATION"
rsync -pR package.json webpack.config.js "$DESTINATION"

if [ -n "$COPY_DATA" ]; then
    rsync -pRr --del public/tiles "$DESTINATION"
    rsync -pRr --del data "$DESTINATION"
fi
