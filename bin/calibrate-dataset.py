#!/usr/bin/env python3
#
# Calibrates an existing dataset against other dataset(s).
#
# Copyright (c) 2020 Carlos Torchia
#
import os
import sys
_dir_path = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'src')
sys.path.append(_dir_path)

from datetime import timedelta
from datetime import date

import transform
import calibration
import climatedb

def get_args(arguments):
    '''
    Determines command line arguments
    '''
    num_arguments = len(arguments)
    if num_arguments < 7:
        print('Usage: ' + arguments[0] + ' <baseline-data-source> <historical-data-source> <projection-data-source> <variable> <baseline-start-year>-<baseline-end-year> <projection-start-year>-<projection-end-year>\n'
              '\n'
              'Calibrates a projection dataset by adding the changes from historical to a\n'
              'specified baseline dataset. This effectively "downscales" the projection\n'
              'dataset to the baseline resolution',
              file=sys.stderr)
        sys.exit(1)

    baseline_data_source = arguments[1]
    historical_data_source = arguments[2]
    projection_data_source = arguments[3]
    variable_name = arguments[4]
    baseline_date_range = arguments[5]
    projection_date_range = arguments[6]

    baseline_start_year, baseline_end_year = [int(year) for year in baseline_date_range.split('-')]
    baseline_start_date = date(baseline_start_year, 1, 1)
    baseline_end_date = date(baseline_end_year, 12, 31)

    projection_start_year, projection_end_year = [int(year) for year in projection_date_range.split('-')]
    projection_start_date = date(projection_start_year, 1, 1)
    projection_end_date = date(projection_end_year, 12, 31)

    return (
        baseline_data_source,
        historical_data_source,
        projection_data_source,
        variable_name,
        baseline_start_date,
        baseline_end_date,
        projection_start_date,
        projection_end_date,
    )

def main(args):
    '''
    The main function
    '''
    (
        baseline_data_source,
        historical_data_source,
        projection_data_source,
        variable_name,
        baseline_start_date,
        baseline_end_date,
        projection_start_date,
        projection_end_date,
    )= get_args(args)

    measurement = transform.to_standard_variable_name(variable_name)
    units = transform.standard_units_from_measurement(measurement)

    climatedb.connect()

    for month in range(1, climatedb.MONTHS_PER_YEAR + 1):
        #print('.', end='', flush=True)
        print('For month %d' % month)
        calibration.calibrate(
            baseline_data_source,
            historical_data_source,
            projection_data_source,
            measurement,
            units,
            baseline_start_date,
            baseline_end_date,
            projection_start_date,
            projection_end_date,
            month
        )

    climatedb.close()

if __name__ == '__main__':
    sys.exit(main(sys.argv))
