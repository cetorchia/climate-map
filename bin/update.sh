#!/bin/bash
#
# Downloads the datasets from the internet and loads them
# into the database and creates map tiles showing the climate colours.
# And loads the geonames. And generates base map tiles.
#
# (c) Carlos Emilio Torchia
#

if [ $# -gt 0 ]; then
    echo "Usage: $(basename $0)" >&2
    exit 1
fi

REPO=$(dirname "$0")/..
cd $REPO

source config/config.sh

BASELINE=$(get_config_value 'baseline') || exit 1
BASELINE_MEASUREMENTS=$(get_config_list $BASELINE 'measurements') || exit 1
PROJECTION_MODELS=$(get_config_keys 'models') || exit 1

#
# Baseline datasets
#
for MEASUREMENT in $BASELINE_MEASUREMENTS; do
    bin/update-dataset.sh $BASELINE $MEASUREMENT || exit $?
done

#
# Model datasets
#
for MODEL in $PROJECTION_MODELS; do
    MEASUREMENTS=$(get_config_list 'models' $MODEL 'measurements') || exit 1
    for MEASUREMENT in $MEASUREMENTS; do
        bin/update-dataset.sh $MODEL $MEASUREMENT || exit $?
    done
done

#
# Geonames database
#
wget https://download.geonames.org/export/dump/admin1CodesASCII.txt -O datsets/admin1CodesASCII.txt || exit 1
wget https://download.geonames.org/export/dump/countryInfo.txt -O datasets/countryInfo.txt || exit 1

wget https://download.geonames.org/export/dump/allCountries.zip -O datasets/allCountries.zip || exit 1
unzip datasets/allCountries.zip -d datasets || exit 1
rm datasets/allCountries.zip

wget https://download.geonames.org/export/dump/alternateNames.zip -O datasets/alternateNames.zip || exit 1
unzip datasets/alternateNames.zip -d datasets || exit 1
rm datasets/alternateNames.zip

bin/load-countries.py datasets/countryInfo.txt || exit 1
bin/load-provinces.py datasets/admin1CodesASCII.txt || exit 1
bin/load-geonames.py datasets/allCountries.txt || exit 1
bin/load-alternate-names.py datasets/alternateNames.txt || exit 1

#
# Map tiles
#
rm -rf datasets/natural-earth
bin/generate-map-tiles.py 0 8
