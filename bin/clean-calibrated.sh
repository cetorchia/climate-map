#!/bin/bash
#
# Cleans up calibrated datasets.
# Calibrated datasets are not needed to run the application.
# They are only needed to generate tiles.
# Once tiles are generated, you can run this script to delete
# the calibrated datasets for the specified model.
#
# Click a bunch of places in the app before running this
# script if you modified the calibration algorithm. Doing this will
# verify the calibrated dataset stored against the on-the-fly
# calibration.
#

if [ -z "$1" -o -n "$2" ]; then
    echo "Usage $(basename "$0") <model>" >&2
    exit 1
fi

DIRNAME=$(dirname "$0")
REPO=$(realpath "$DIRNAME/..")
MODEL="$1"

rm -vi "$REPO/data/$MODEL".*-calibrated*
