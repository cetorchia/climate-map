#!/bin/bash
#
# Gets the specified dataset.
#

if [ $# != 4 ]; then
    echo "Usage: $(basename $0) <dataset> <variable> <start-year> <end-year>" >&2
    exit 1
fi

DATASET="$1"
VARIABLE="$2"
START_YEAR="$3"
END_YEAR="$4"

case $DATASET in
    TerraClimate)
        URL=http://thredds.northwestknowledge.net:8080/thredds/fileServer/TERRACLIMATE_ALL/summaries
        BASENAME=TerraClimate${START_YEAR}${END_YEAR}_${VARIABLE}.nc
        ;;
    CanESM5)
        ;;
    MRI-ESM2-0)
        ;;
    CNRM-CM6-1-HR)
        ;;
esac

wget $URL/$BASENAME -O datasets/$BASENAME
