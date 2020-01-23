#!/bin/bash
#
# Runs transformation for all months for a date range.
# Loads data into db.
#

ROOT_FOLDER=$(dirname $0)/..
SCRIPT=$(dirname $0)/transform-dataset.py

if [ -z "$5" ]; then
    echo "Usage: $(basename $0) <input-dataset> <variable-name> <start-year> <end-year> <data-source>"
fi

INPUT_FILE="$1"
VARIABLE_NAME="$2"
START_YEAR="$3"
END_YEAR="$4"
DATA_SOURCE="$5"

OUTPUT_DB=localhost:climate_map:climate_map

# Monthly normals
for MONTH in $(seq 1 12); do
    echo $VARIABLE_NAME $START_YEAR $END_YEAR $MONTH
    $SCRIPT $INPUT_FILE $OUTPUT_DB $VARIABLE_NAME $START_YEAR $END_YEAR $MONTH $DATA_SOURCE || exit 1
done
