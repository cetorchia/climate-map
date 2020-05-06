#!/bin/bash
#
# Runs the tiles-from-dataset.py script on the specified
# dataset and date range for all date ranges and experiments
# defined in config-update.yaml.
#

if [ -z "$2" -o -n "$3" ]; then
    echo "Usage: $(basename $0) <model> <measurement>" >&2
    echo >&2
    echo "  E.g. $(basename $0) CanESM5 tavg" >&2
    echo "       $(basename $0) TerraClimate potet" >&2
    exit 1
fi

SCRIPT='bin/tiles-from-dataset.py'

MODEL="$1"
MEASUREMENT="$2"

case $MEASUREMENT in
    tavg|precip|potet)
        ;;
    *)
        exit 0
        ;;
esac

source config/config.sh

if [ -n "$(get_config_value $MODEL 2>&-)" ]; then
    DATE_RANGES=$(get_config_value $MODEL 'date_range') || exit 1
    DATA_SOURCES="$MODEL"
    CALIBRATED=''
else
    DATE_RANGES=$(get_config_list 'models' $MODEL 'date_ranges') || exit 1
    DATA_SOURCES=''
    for EXPERIMENT in $(get_config_list 'models' $MODEL 'experiments'); do
        DATA_SOURCES="$DATA_SOURCES $MODEL.$EXPERIMENT"
    done
    CALIBRATED='--calibrated'
fi

for DATA_SOURCE in $DATA_SOURCES; do
    for DATE_RANGE in $DATE_RANGES; do
        DATE_RANGE_ARRAY=($(echo "$DATE_RANGE" | tr '-' '\n'))
        START_YEAR=${DATE_RANGE_ARRAY[0]}
        END_YEAR=${DATE_RANGE_ARRAY[1]}

        echo $DATA_SOURCE $MEASUREMENT $START_YEAR $END_YEAR
        $SCRIPT $CALIBRATED $DATA_SOURCE $MEASUREMENT $START_YEAR $END_YEAR || exit $?
    done
done
