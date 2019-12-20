#!/bin/bash
#
# Runs transformation for all months for a date range.
# The input must contain all months data.
#

ROOT_FOLDER=$(dirname $0)/..
SCRIPT=$(dirname $0)/transform-dataset.py

if [ -z "$4" ]; then
    echo "Usage: $(basename $0) <dataset-filename> <variable_name> <start-year> <end-year>"
fi

INPUT_FILENAME="$1"
VARIABLE_NAME="$2"
START_YEAR="$3"
END_YEAR="$4"

OUTPUT_FOLDER="$ROOT_FOLDER/public/data/$START_YEAR-$END_YEAR/"

# Annual normals
echo $VARIABLE_NAME $START_YEAR $END_YEAR
$SCRIPT $INPUT_FILENAME $OUTPUT_FOLDER $VARIABLE_NAME $START_YEAR $END_YEAR || exit 1

# Monthly normals
for MONTH in $(seq 1 12); do
    echo $VARIABLE_NAME $START_YEAR $END_YEAR $MONTH
    $SCRIPT $INPUT_FILENAME $OUTPUT_FOLDER $VARIABLE_NAME $START_YEAR $END_YEAR $MONTH || exit 1
done
