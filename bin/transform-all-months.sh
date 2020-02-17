#!/bin/bash
#
# Runs transformation for all months for a date range.
# Loads data into db.
#

ROOT_FOLDER=$(dirname $0)/..
SCRIPT=$(dirname $0)/transform-dataset.py

if [[ $# < 5 ]]; then
    echo "Usage: $(basename $0) <input-dataset1> [input-dataset2] ... <variable_name> <start-year> <end-year> <data-source>"
fi

INPUT_FILES="$1"; shift
while (( $# > 4 )); do
    INPUT_FILES="$INPUT_FILES $1"; shift
done

VARIABLE_NAME="$1"
START_YEAR="$2"
END_YEAR="$3"
DATA_SOURCE="$4"

OUTPUT_FILE=db

# Monthly normals
for MONTH in $(seq 1 12); do
    echo $VARIABLE_NAME $START_YEAR $END_YEAR $MONTH $DATA_SOURCE
    $SCRIPT $INPUT_FILES $OUTPUT_FILE $VARIABLE_NAME $START_YEAR $END_YEAR $MONTH $DATA_SOURCE || exit 1
done
