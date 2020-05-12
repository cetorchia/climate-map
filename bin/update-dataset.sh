#!/bin/bash
#
# Retrieves a dataset and loads it into the database.
#
# (c) 2020 Carlos Emilio Torchia
#

if [ -z "$2" -o -n "$4" ]; then
    echo "Usage: $(basename $0) <model> <measurement> [frequency]" >&2
    echo >&2
    echo "Frequency defaults to 'mon', can be set to 'day'" >&2
    exit 1
fi

MODEL="$1"
MEASUREMENT="$2"
FREQUENCY="$3"

REPO=$(dirname "$0")/..
cd $REPO

source config/config.sh config/config-update.yaml

case $MODEL in
    TerraClimate)
        case $MEASUREMENT in
            tavg)
                VARIABLES='tmin tmax'
                ;;
            tmin)
                VARIABLES='tmin'
                ;;
            tmax)
                VARIABLES='tmax'
                ;;
            precip)
                VARIABLES='ppt'
                ;;
            potet)
                VARIABLES='pet'
                ;;
            wind)
                VARIABLES='ws'
                ;;
            elevation)
                VARIABLES='elevation'
                ;;
            *)
                echo 'Unknown measurement:' $MEASUREMENT >&2
                exit 1
                ;;
        esac

        DATE_RANGE=$(get_config_value $MODEL 'date_range') || exit 1

        DATE_RANGE_ARRAY=($(echo "$DATE_RANGE" | tr '-' '\n'))
        START=${DATE_RANGE_ARRAY[0]}
        END=${DATE_RANGE_ARRAY[1]}

        for VARIABLE in $VARIABLES; do
            bin/get-dataset.py TerraClimate $VARIABLE || exit $?
        done

        case MEASUREMENT in
            elevation)
                bin/load-nontemporal-data.py --ignore-scale-factor datasets/TerraClimate-elevation.nc elevation TerraClimate || exit $?
                ;;
            tavg)
                bin/transform-dataset.py datasets/TerraClimate-tmin.nc datasets/TerraClimate-tmax.nc tavg $START $END TerraClimate || exit $?
                ;;
            *)
                bin/transform-dataset.py datasets/TerraClimate-$VARIABLE.nc $VARIABLE $START $END TerraClimate || exit $?
                ;;
        esac
        ;;

    worldclim)
        case $MEASUREMENT in
            tavg)
                VARIABLE='tavg'
                ;;
            tmin)
                VARIABLE='tmin'
                ;;
            tmax)
                VARIABLE='tmax'
                ;;
            precip)
                VARIABLE='prec'
                ;;
            wind)
                VARIABLE='wind'
                ;;
            vapr)
                VARIABLE='vapr'
                ;;
            *)
                echo 'Unknown measurement:' $MEASUREMENT >&2
                exit 1
                ;;
        esac

        DATE_RANGE=$(get_config_value $MODEL 'date_range') || exit 1

        DATE_RANGE_ARRAY=($(echo "$DATE_RANGE" | tr '-' '\n'))
        START=${DATE_RANGE_ARRAY[0]}
        END=${DATE_RANGE_ARRAY[1]}

        bin/get-dataset.py worldclim $VARIABLE || exit $?

        unzip datasets/worldclim-$VARIABLE.zip -d datasets/ || exit $?
        bin/transform-dataset.py datasets/wc2.1_2.5m_$VARIABLE/ $VARIABLE $START $END worldclim || exit $?
        ;;

    *)
        # CMIP6 forecast
        case $MEASUREMENT in
            tavg)
                VARIABLE='tas'
                ;;
            tmin)
                VARIABLE='tasmin'
                ;;
            tmax)
                VARIABLE='tasmax'
                ;;
            precip)
                VARIABLE='pr'
                ;;
            potet)
                VARIABLE='evspsblpot'
                ;;
            wind)
                VARIABLE='sfcWind'
                ;;
            *)
                echo 'Unknown measurement:' $MEASUREMENT >&2
                exit 1
                ;;
        esac

        BASELINE=$(get_config_value 'baseline') || exit 1
        HISTORICAL_DATE_RANGE=$(get_config_value $BASELINE 'date_range') || exit 1
        PROJECTION_DATE_RANGES=$(get_config_list 'models' $MODEL 'date_ranges') || exit 1
        EXPERIMENTS=$(get_config_list 'models' $MODEL 'experiments') || exit 1

        DATE_RANGE_ARRAY=($(echo "$HISTORICAL_DATE_RANGE" | tr '-' '\n'))
        HSTART=${DATE_RANGE_ARRAY[0]}
        HEND=${DATE_RANGE_ARRAY[1]}

        HISTORICAL="$MODEL.historical"

        bin/get-dataset.py $HISTORICAL $VARIABLE $FREQUENCY || exit $?
        FILE=datasets/$HISTORICAL-$VARIABLE.nc
        bin/transform-dataset.py $FILE $VARIABLE $HSTART $HEND $HISTORICAL || exit $?

        for EXPERIMENT in $EXPERIMENTS; do
            PROJECTION=$MODEL.$EXPERIMENT

            bin/get-dataset.py $PROJECTION $VARIABLE $FREQUENCY || exit $?
            FILE=datasets/$PROJECTION-$VARIABLE.nc

            for PROJECTION_DATE_RANGE in $PROJECTION_DATE_RANGES; do
                DATE_RANGE_ARRAY=($(echo "$PROJECTION_DATE_RANGE" | tr '-' '\n'))
                PSTART=${DATE_RANGE_ARRAY[0]}
                PEND=${DATE_RANGE_ARRAY[1]}

                bin/transform-dataset.py $FILE $VARIABLE $PSTART $PEND $PROJECTION || exit $?

                bin/calibrate-dataset.py $BASELINE $HISTORICAL $PROJECTION $MEASUREMENT $HISTORICAL_DATE_RANGE $PROJECTION_DATE_RANGE || exit $?
            done
        done
        ;;
esac

bin/generate-tiles.sh "$MODEL" "$MEASUREMENT"
