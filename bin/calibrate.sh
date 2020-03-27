#!/bin/bash
#
# Runs the calibrate-dataset.py script on the specified
# dataset for all scenarios, date ranges, and measurements.
#

if [ -z "$1" -o -n "$2" ]; then
    echo "Usage: $(basename $0) <model>" >&2
    echo "E.g. $(basename $0) CanESM5" >&2
    exit 1
fi

SCRIPT='bin/calibrate-dataset.py'
BASELINE='TerraClimate'
MEASUREMENTS='tmin tavg precip'
SCENARIOS='ssp245 ssp585'
HISTORICAL_DATE_RANGE='1981-2010'
PROJECTION_DATE_RANGES='2015-2045 2045-2075'

MODEL="$1"
HISTORICAL=$MODEL.historical

for SCENARIO in $SCENARIOS; do
    for PROJECTION_DATE_RANGE in $PROJECTION_DATE_RANGES; do
        for MEASUREMENT in $MEASUREMENTS; do
            echo $BASELINE $HISTORICAL $MODEL.$SCENARIO $MEASUREMENT $HISTORICAL_DATE_RANGE $PROJECTION_DATE_RANGE
            $SCRIPT $BASELINE $HISTORICAL $MODEL.$SCENARIO $MEASUREMENT $HISTORICAL_DATE_RANGE $PROJECTION_DATE_RANGE || exit $?
        done
    done
done
