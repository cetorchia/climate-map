#!/bin/bash
#
# Runs transformation for all months for a date range.
#

ROOT_FOLDER=$(dirname $0)/..
SCRIPT=$(dirname $0)/transform-netcdf.py

if [ -z "$3" ]; then
    echo "Usage: $(basename $0) <netCDF4-filename> <start-year> <end-year>"
fi

INPUT_FILENAME="$1"
START_YEAR="$2"
END_YEAR="$3"

OUTPUT_FOLDER="$ROOT_FOLDER/public/data/$START_YEAR-$END_YEAR/"
VARIABLE_NAME=$(basename $INPUT_FILENAME | tr "." "\n" | head -1)

case $VARIABLE_NAME in
    air)
        OUTPUT_NAME=temperature
        ;;
    precip)
        OUTPUT_NAME=precipitation
        ;;
    *)
        OUTPUT_NAME=$VARIABLE_NAME
esac

# Annual normals
echo $VARIABLE_NAME $START_YEAR $END_YEAR
OUTPUT_FILE=$OUTPUT_FOLDER/$OUTPUT_NAME.png
$SCRIPT $INPUT_FILENAME $OUTPUT_FILE $VARIABLE_NAME $START_YEAR $END_YEAR

# Monthly normals
for MONTH in $(seq 1 12); do
    echo $VARIABLE_NAME $START_YEAR $END_YEAR $MONTH
    OUTPUT_MONTH=$(printf '%02d' $MONTH)
    OUTPUT_FILE=$OUTPUT_FOLDER/$OUTPUT_NAME-$OUTPUT_MONTH.png
    $SCRIPT $INPUT_FILENAME $OUTPUT_FILE $VARIABLE_NAME $START_YEAR $END_YEAR $MONTH
done
