#!/usr/bin/env python3
#
# Calibrates projected climate normals against
# baseline historical data.
#
# Copyright (c) 2020 Carlos Torchia
#

import numpy as np

import climatedb
import arrays
import pack

ABSOLUTE_DIFFERENCE_MEASUREMENTS = 'tavg', 'tmin', 'tmax', 'precip'

def calibrate(
        baseline_data_source_code,
        historical_data_source_code,
        projection_data_source_code,
        measurement,
        units,
        baseline_start_date,
        baseline_end_date,
        projection_start_date,
        projection_end_date,
        month
):
    '''
    Adds projected differences to the baseline data.
    '''
    unit_id = climatedb.fetch_unit(units)['id']
    measurement_id = climatedb.fetch_measurement(measurement)['id']

    baseline_data_source = climatedb.fetch_data_source(baseline_data_source_code)
    if not baseline_data_source['baseline']:
        raise Exception('Expected data source %s to be flagged as "baseline"' % baseline_data_source_code)

    historical_data_source = climatedb.fetch_data_source(historical_data_source_code)
    projection_data_source = climatedb.fetch_data_source(projection_data_source_code)

    print('Using historical dataset %s-%d-%d-%s-%s' % (
        historical_data_source_code,
        baseline_start_date.year,
        baseline_end_date.year,
        measurement,
        units
    ))
    historical_dataset = climatedb.fetch_dataset(
        historical_data_source['id'],
        measurement_id,
        unit_id,
        baseline_start_date,
        baseline_end_date,
        calibrated=False
    )
    historical_lat, historical_lon, historical_data = climatedb.fetch_normals_from_dataset(historical_dataset, month)

    print('And projection dataset %s-%d-%d-%s-%s' % (
        projection_data_source_code,
        projection_start_date.year,
        projection_end_date.year,
        measurement,
        units
    ))
    projection_dataset = climatedb.fetch_dataset(
        projection_data_source['id'],
        measurement_id,
        unit_id,
        projection_start_date,
        projection_end_date,
        calibrated=False
    )
    projection_lat, projection_lon, projection_data = climatedb.fetch_normals_from_dataset(projection_dataset, month)

    if projection_data.shape != historical_data.shape:
        raise Exception('Expected historical data to have the same shape as projection')

    if np.any(projection_lat != historical_lat):
        raise Exception('Expected historical latitudes to be the same as projection latitudes')

    if np.any(projection_lon != historical_lon):
        raise Exception('Expected historical longitudes to be the same as projection longitudes')

    if measurement in ABSOLUTE_DIFFERENCE_MEASUREMENTS:
        print('Using absolute difference')
        differences = projection_data - historical_data
    else:
        print('Using relative difference')
        differences = projection_data / historical_data

    print('Against baseline dataset %s-%d-%d-%s-%s' % (
        baseline_data_source_code,
        baseline_start_date.year,
        baseline_end_date.year,
        measurement,
        units
    ))
    baseline_dataset = climatedb.fetch_dataset(
        baseline_data_source['id'],
        measurement_id,
        unit_id,
        baseline_start_date,
        baseline_end_date,
        calibrated=False
    )
    baseline_lat, baseline_lon, baseline_data = climatedb.fetch_normals_from_dataset(baseline_dataset, month)

    downscaled_differences = arrays.downscale_array(
        baseline_lat,
        baseline_lon,
        projection_lat,
        projection_dataset['lat_delta'],
        projection_lon,
        projection_dataset['lon_delta'],
        differences
    )

    if downscaled_differences.shape != baseline_data.shape:
        raise Exception('Expected downscaled differences to have the same shape as baseline data')

    if measurement in ABSOLUTE_DIFFERENCE_MEASUREMENTS:
        calibrated_data = baseline_data + downscaled_differences
    else:
        calibrated_data = np.round(baseline_data * downscaled_differences)

    if np.any((calibrated_data > pack.OUTPUT_DTYPE_MAX) | (calibrated_data < pack.OUTPUT_DTYPE_MIN)):
        raise Exception('Calibrated data is out of bounds for %s' % pack.OUTPUT_DTYPE)
    else:
        calibrated_data = calibrated_data.astype(pack.OUTPUT_DTYPE)

    climatedb.save_normals(
        baseline_lat,
        baseline_lon,
        units,
        calibrated_data,
        measurement,
        projection_start_date,
        projection_end_date,
        month,
        projection_data_source['code'],
        calibrated=True
    )

    print('Created calibrated dataset %s-%d-%d-%s-%s-calibrated' % (
        projection_data_source_code,
        projection_start_date.year,
        projection_end_date.year,
        measurement,
        units
    ))

def calibrate_location(dataset, lat, lon):
    '''
    Calibrates the climate normals at a specific location
    against historical data.
    '''
    measurement = climatedb.fetch_measurement_by_id(dataset['measurement_id'])['code']
    baseline_data_source_id = climatedb.fetch_baseline_data_source()
    baseline_start_date, baseline_end_date = list(climatedb.fetch_date_ranges_by_data_source_id(baseline_data_source_id))[0]
    baseline_dataset = climatedb.fetch_dataset(
        baseline_data_source_id,
        dataset['measurement_id'],
        dataset['unit_id'],
        baseline_start_date,
        baseline_end_date,
        calibrated=False
    )

    historical_data_source_id = climatedb.fetch_historical_data_source(dataset['data_source_id'])
    historical_dataset = climatedb.fetch_dataset(
        historical_data_source_id,
        dataset['measurement_id'],
        dataset['unit_id'],
        baseline_start_date,
        baseline_end_date,
        calibrated=False
    )

    projection_dataset = climatedb.fetch_dataset(
        dataset['data_source_id'],
        dataset['measurement_id'],
        dataset['unit_id'],
        dataset['start_date'],
        dataset['end_date'],
        calibrated=False
    )

    actual_lat, actual_lon, historical_normals_arr = climatedb.fetch_monthly_normals(historical_dataset, lat, lon)
    actual_lat, actual_lon, projection_normals_arr = climatedb.fetch_monthly_normals(projection_dataset, lat, lon)
    actual_lat, actual_lon, baseline_normals_arr = climatedb.fetch_monthly_normals(baseline_dataset, lat, lon)

    if measurement in ABSOLUTE_DIFFERENCE_MEASUREMENTS:
        normals_arr = baseline_normals_arr + projection_normals_arr - historical_normals_arr
    else:
        normals_arr = baseline_normals_arr * projection_normals_arr / historical_normals_arr

    return actual_lat, actual_lon, normals_arr
