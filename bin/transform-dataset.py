#!/usr/bin/env python3
#
# Transforms dataset files to various data formats for use
# as climate data.
#
# Copyright (c) 2020 Carlos Torchia
#
import os
import sys
_dir_path = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'src')
sys.path.append(_dir_path)

from datetime import timedelta
from datetime import datetime

import transform
import climatedb
import pack

def get_args(arguments):
    '''
    Determines command line arguments
    '''
    num_arguments = len(arguments)
    if num_arguments < 5:
        print('Usage: ' + arguments[0] + ' <dataset-filename1> [dataset-filename2] ... <var> <start-year> <end-year> <data-source>', file=sys.stderr)
        sys.exit(1)

    input_files = arguments[1:-4]
    rest_of_arguments = arguments[-4:]

    variable_name = rest_of_arguments[0]
    start_year = int(rest_of_arguments[1])
    end_year = int(rest_of_arguments[2])
    data_source = rest_of_arguments[3]

    return (input_files, variable_name, start_year, end_year, data_source)

def get_input_fmt(input_file):
    '''
    Gives the format of the specified input file.
    '''
    if input_file.endswith(os.path.sep):
        return 'folder'
    else:
        input_fmt = input_file.split('.')[-1]

        if input_fmt not in ('nc', 'tif', 'bil'):
            raise Exception('Unsupported input format ' + input_fmt)

        return input_fmt

def main(args):
    '''
    The main function
    '''
    input_files, variable_name, start_year, end_year, data_source = get_args(args)

    # Extract normals from datasets
    def get_normals_function(month, start_time, end_time):
        def get_normals(input_file):
            input_fmt = get_input_fmt(input_file)

            if input_fmt == 'nc':
                return transform.normals_from_netcdf4(
                    input_file,
                    variable_name,
                    start_time,
                    end_time,
                    month
                )

            elif input_fmt in ('tif', 'bil'):
                return transform.normals_from_geotiff(input_file, input_fmt)

            elif input_fmt == 'folder':
                return transform.normals_from_folder(input_file, variable_name, month)

            else:
                raise Exception('Unexpected input format "%s"' % input_fmt)

        return get_normals

    climatedb.connect()

    for month in range(1, climatedb.MONTHS_PER_YEAR + 1):
        print(data_source, variable_name, start_year, end_year, month)

        if month > 0:
            start_time = datetime(start_year, month, 1)
            # This will set the end time to the last second of the last day of the
            # specified month in the specified end year.
            # Credit to https://stackoverflow.com/a/4131114 for the div/mod by 12
            end_time = datetime(end_year + month // 12, month % 12 + 1, 1) - timedelta(seconds=1)
        else:
            start_time = datetime(start_year, 1, 1)
            end_time = datetime(end_year + 1, 1, 1) - timedelta(seconds=1)

        lat_arr, lon_arr, units, normals = \
            transform.aggregate_normals(input_files, get_normals_function(month, start_time, end_time))

        units, normals = transform.data_to_standard_units(units, normals, month)
        lon_arr, normals = transform.normalize_longitudes(lon_arr, normals)
        normals = pack.pack_array(normals)

        measurement = transform.to_standard_variable_name(variable_name)

        climatedb.save_normals(
            lat_arr,
            lon_arr,
            units,
            normals,
            measurement,
            start_time,
            end_time,
            month,
            data_source
        )

    climatedb.close()

    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
