#!/bin/bash
#
# Runs transformation for all months for a date range.
#
# The folder must be a standard WorldClim folder as the
# folder name will be used to determine all filenames.
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

case $VARIABLE_NAME in
    tmin)
        OUTPUT_NAME=temperature-min
        ;;
    tmax)
        OUTPUT_NAME=temperature-max
        ;;
    tavg|air)
        OUTPUT_NAME=temperature-avg
        ;;
    precip)
        OUTPUT_NAME=precipitation
        ;;
    *)
        OUTPUT_NAME=$VARIABLE_NAME
esac

# Monthly normals
for MONTH in $(seq 1 12); do
    echo $VARIABLE_NAME $START_YEAR $END_YEAR $MONTH
    INPUT_MONTH=$(printf '%02d' $MONTH)
    INPUT_FILENAME="$INPUT_FOLDER/${INPUT_PREFIX}_$INPUT_MONTH.tif"
    OUTPUT_MONTH=$INPUT_MONTH
    OUTPUT_FILE=$OUTPUT_FOLDER/$OUTPUT_NAME-$OUTPUT_MONTH.png
    $SCRIPT $INPUT_FILENAME $OUTPUT_FILE $VARIABLE_NAME $START_YEAR $END_YEAR $MONTH || exit 1
done
