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
wget https://download.geonames.org/export/dump/admin1CodesASCII.txt -O datsets/admin1CodesASCII.txt
wget https://download.geonames.org/export/dump/countryInfo.txt -O datasets/countryInfo.txt

wget https://download.geonames.org/export/dump/allCountries.zip -O datasets/allCountries.zip
unzip datasets/allCountries.zip -d datasets
rm datasets/allCountries.zip

wget https://download.geonames.org/export/dump/alternateNames.zip -O datasets/alternateNames.zip
unzip datasets/alternateNames.zip -d datasets
rm datasets/alternateNames.zip

bin/load-countries.py datasets/countryInfo.txt
bin/load-provinces.py datasets/admin1CodesASCII.txt
bin/load-geonames.py datasets/allCountries.txt
bin/load-alternate-names.py datasets/alternateNames.txt

#
# Map tiles
#
rm -rf datasets/natural-earth
bin/generate-map-tiles.py 0 8
