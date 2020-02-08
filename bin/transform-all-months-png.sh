#!/bin/bash
#
# Runs transformation for all months for a date range.
# Loads data into PNG tiles.
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

OUTPUT_FOLDER="$ROOT_FOLDER/public/data/$DATA_SOURCE/$START_YEAR-$END_YEAR/"

case $VARIABLE_NAME in
    tmin|tasmin)
        OUTPUT_NAME=temperature-min
        ;;
    tmax|tasmax)
        OUTPUT_NAME=temperature-max
        ;;
    tavg|air|tas)
        OUTPUT_NAME=temperature-avg
        ;;
    precip|pr|ppt)
        OUTPUT_NAME=precipitation
        ;;
    *)
        OUTPUT_NAME=$VARIABLE_NAME
esac

# Annual normals
echo $VARIABLE_NAME $START_YEAR $END_YEAR
TILE_FOLDER=$OUTPUT_FOLDER/tiles/$OUTPUT_NAME
$SCRIPT $INPUT_FILES $TILE_FOLDER $VARIABLE_NAME $START_YEAR $END_YEAR 0 $DATA_SOURCE || exit 1

# Monthly normals
for MONTH in $(seq 1 12); do
    echo $VARIABLE_NAME $START_YEAR $END_YEAR $MONTH
    OUTPUT_MONTH=$(printf '%02d' $MONTH)
    TILE_FOLDER=$OUTPUT_FOLDER/tiles/$OUTPUT_NAME-$OUTPUT_MONTH
    $SCRIPT $INPUT_FILES $TILE_FOLDER $VARIABLE_NAME $START_YEAR $END_YEAR $MONTH $DATA_SOURCE || exit 1
done
