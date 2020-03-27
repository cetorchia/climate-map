#!/bin/bash
#
# Runs the tiles-from-dataset.py script on the specified
# dataset and date range for all measurements.
#

if [ -z "$1" -o -n "$2" ]; then
    echo "Usage: $(basename $0) <model>" >&2
    echo >&2
    echo "  E.g. $(basename $0) CanESM5" >&2
    echo "       $(basename $0) TerraClimate" >&2
    exit 1
fi

SCRIPT='bin/tiles-from-dataset.py'
MEASUREMENTS='tavg precip'

MODEL="$1"

case $MODEL in
    TerraClimate)
        DATE_RANGES='1981-2010'
        DATA_SOURCES='TerraClimate'
        CALIBRATED=''
        ;;
    worldclim)
        DATE_RANGES='1960-1990'
        DATA_SOURCES='worldclim'
        CALIBRATED=''
        ;;
    *)
        DATE_RANGES='2015-2045 2045-2075'
        DATA_SOURCES="$MODEL.ssp245 $MODEL.ssp585"
        CALIBRATED='--calibrated'
        ;;
esac

for DATA_SOURCE in $DATA_SOURCES; do
    for DATE_RANGE in $DATE_RANGES; do
        DATE_RANGE_ARRAY=($(echo "$DATE_RANGE" | tr '-' '\n'))
        START_YEAR=${DATE_RANGE_ARRAY[0]}
        END_YEAR=${DATE_RANGE_ARRAY[1]}

        for MEASUREMENT in $MEASUREMENTS; do
            echo $DATA_SOURCE $MEASUREMENT $START_YEAR $END_YEAR
            $SCRIPT $CALIBRATED $DATA_SOURCE $MEASUREMENT $START_YEAR $END_YEAR || exit $?
        done
    done
done
