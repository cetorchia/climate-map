#!/bin/bash
#
# Runs transformation for all months for a date range.
#
# The folder must be a standard WorldClim folder as the
# filenames will be used to determine each month.
#

ROOT_FOLDER=$(dirname $0)/..
SCRIPT=$(dirname $0)/transform-dataset.py

if [ -z "$4" ]; then
    echo "Usage: $(basename $0) <dataset-folder> <variable_name> <start-year> <end-year>"
fi

INPUT_FOLDER="$1"
VARIABLE_NAME="$2"
START_YEAR="$3"
END_YEAR="$4"

OUTPUT_FOLDER="$ROOT_FOLDER/public/data/$START_YEAR-$END_YEAR/"
INPUT_PREFIX=$(basename $INPUT_FOLDER)

# Monthly normals
for MONTH in $(seq 1 12); do
    echo $VARIABLE_NAME $START_YEAR $END_YEAR $MONTH
    INPUT_MONTH=$(printf '%02d' $MONTH)
    INPUT_FILENAME="$INPUT_FOLDER/${INPUT_PREFIX}_$INPUT_MONTH.tif"
    $SCRIPT $INPUT_FILENAME $OUTPUT_FOLDER $VARIABLE_NAME $START_YEAR $END_YEAR $MONTH || exit 1
done
