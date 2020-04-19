#!/bin/bash
#
# Work-in-progress: the goal is to have all
# commands to load the desired data in the database.
#
# This will do everything from download the datasets from the
# servers to creating map tiles showing the climate colours.
#
# TODO: Add temperature and precipitation datasets here. I did these
# manually before I created this helper script.
#

if [ $# -gt 0 ]; then
    echo "Usage: $(basename $0)" >&2
    exit 1
fi

REPO=$(dirname "$0")/..

cd $REPO

#
# Baseline datasets
#

# TerraClimate potential evapotranspiration
bin/get-dataset.py TerraClimate pet
bin/transform-dataset.py datasets/TerraClimate19812010_pet.nc potet 1981 2010 TerraClimate
bin/tiles-from-dataset.py TerraClimate potet 1981 2010

#
# Model datasets
#

# CNRM potential evapotranspiration
bin/get-dataset.py CNRM-CM6-1-HR.historical evspsblpot
bin/transform-dataset.py datasets/evspsblpot_Emon_CNRM-CM6-1-HR_historical_r1i1p1f2_gr_185001-201412.nc evspsblpot 1981 2010 CNRM-CM6-1-HR.historical

bin/get-dataset.py CNRM-CM6-1-HR.ssp245 evspsblpot
bin/transform-dataset.py datasets/evspsblpot_Emon_CNRM-CM6-1-HR_ssp245_r1i1p1f2_gr_201501-210012.nc evspsblpot 2015 2045 CNRM-CM6-1-HR.ssp245
bin/transform-dataset.py datasets/evspsblpot_Emon_CNRM-CM6-1-HR_ssp245_r1i1p1f2_gr_201501-210012.nc evspsblpot 2045 2075 CNRM-CM6-1-HR.ssp245
bin/calibrate-dataset.py TerraClimate CNRM-CM6-1-HR.historical CNRM-CM6-1-HR.ssp245 potet 1981-2010 2015-2045
bin/calibrate-dataset.py TerraClimate CNRM-CM6-1-HR.historical CNRM-CM6-1-HR.ssp245 potet 1981-2010 2045-2075
bin/tiles-from-dataset.py --calibrated CNRM-CM6-1-HR.ssp245 potet 2015 2045
bin/tiles-from-dataset.py --calibrated CNRM-CM6-1-HR.ssp245 potet 2045 2075

bin/get-dataset.py CNRM-CM6-1-HR.ssp585 evspsblpot
bin/transform-dataset.py datasets/evspsblpot_Emon_CNRM-CM6-1-HR_ssp585_r1i1p1f2_gr_201501-210012.nc evspsblpot 2015 2045 CNRM-CM6-1-HR.ssp585
bin/transform-dataset.py datasets/evspsblpot_Emon_CNRM-CM6-1-HR_ssp585_r1i1p1f2_gr_201501-210012.nc evspsblpot 2045 2075 CNRM-CM6-1-HR.ssp585
bin/calibrate-dataset.py TerraClimate CNRM-CM6-1-HR.historical CNRM-CM6-1-HR.ssp585 potet 1981-2010 2015-2045
bin/calibrate-dataset.py TerraClimate CNRM-CM6-1-HR.historical CNRM-CM6-1-HR.ssp585 potet 1981-2010 2045-2075
bin/tiles-from-dataset.py --calibrated CNRM-CM6-1-HR.ssp585 potet 2015 2045
bin/tiles-from-dataset.py --calibrated CNRM-CM6-1-HR.ssp585 potet 2045 2075

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
