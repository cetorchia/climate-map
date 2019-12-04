#!/bin/bash
#
# Runs transformation for all months for a date range.
#

SCRIPT=$(dirname $0)/transform-netcdf.py

if [ -z "$3" ]; then
    echo "Usage: $(basename $0) <netCDF4-filename> <start-year> <end-year>"
fi

INPUT_FILENAME="$1"
START_YEAR="$2"
END_YEAR="$3"

OUTPUT_FOLDER="public/data/$START_YEAR-$END_YEAR/"
VARIABLE_NAME=$(basename $INPUT_FILENAME | tr "." "\n" | head -1)

# Annual normals
echo $VARIABLE_NAME $START_YEAR $END_YEAR
$SCRIPT $INPUT_FILENAME $OUTPUT_FOLDER $VARIABLE_NAME $START_YEAR $END_YEAR

# Monthly normals
for MONTH in $(seq 1 12); do
    echo $VARIABLE_NAME $START_YEAR $END_YEAR $MONTH
    $SCRIPT $INPUT_FILENAME $OUTPUT_FOLDER $VARIABLE_NAME $START_YEAR $END_YEAR $MONTH
done
