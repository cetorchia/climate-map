#!/usr/bin/env python3
#
# Transforms dataset files to various data formats for use
# as climate data.
#
# Copyright (c) 2019 Carlos Torchia
#
import os
import sys
dir_path = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'src')
sys.path.append(dir_path)

from datetime import timedelta
from datetime import datetime

import climatetransform
import climatedb

def get_args(arguments):
    '''
    Determines command line arguments
    '''
    num_arguments = len(arguments)
    if num_arguments < 8:
        print('Usage: ' + arguments[0] + ' <dataset-filename1> [dataset-filename2] ... <output-filename> <var> <start-year> <end-year> <month|0> <data-source>', file=sys.stderr)
        print('0 means all months')
        sys.exit(1)

    input_files = arguments[1:-6]
    rest_of_arguments = arguments[-6:]

    output_file = rest_of_arguments[0]
    variable_name = rest_of_arguments[1]
    start_year = int(rest_of_arguments[2])
    end_year = int(rest_of_arguments[3])
    month = int(rest_of_arguments[4])
    data_source = rest_of_arguments[5]

    if month > 0:
        start_time = datetime(start_year, month, 1)
        # This will set the end time to the last second of the last day of the
        # specified month in the specified end year.
        # Credit to https://stackoverflow.com/a/4131114 for the div/mod by 12
        end_time = datetime(end_year + month // 12, month % 12 + 1, 1) - timedelta(seconds=1)
    else:
        start_time = datetime(start_year, 1, 1)
        end_time = datetime(end_year + 1, 1, 1) - timedelta(seconds=1)

    return (input_files, output_file, variable_name, month, start_time, end_time, data_source)

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

def get_output_fmt(output_file):
    '''
    Gives the format of the specified output file.
    '''
    if output_file.find(os.path.sep + 'tiles' + os.path.sep) != - 1 or output_file.startswith('tiles' + os.path.sep):
        return 'tiles'
    elif climatedb.CONN_STR_RE.search(output_file):
        return 'db'
    else:
        output_fmt = output_file.split('.')[-1]

        if output_fmt not in ('png', 'jpeg'):
            raise Exception('Unsupported output format ' + output_fmt)

        return output_fmt

def main(args):
    '''
    The main function
    '''
    input_files, output_file, variable_name, month, start_time, end_time, data_source = get_args(args)

    # Extract normals from datasets
    def get_normals(input_file):
        input_fmt = get_input_fmt(input_file)

        if input_fmt == 'nc':
            return climatetransform.normals_from_netcdf4(
                input_file,
                variable_name,
                start_time,
                end_time,
                month
            )

        elif input_fmt in ('tif', 'bil'):
            return climatetransform.normals_from_geotiff(input_file, input_fmt)

        elif input_fmt == 'folder':
            return climatetransform.normals_from_folder(input_file, variable_name, month)

        else:
            raise Exception('Unexpected input format "%s"' % input_fmt)

    lat_arr, lon_arr, units, normals = climatetransform.aggregate_normals(input_files, get_normals)

    # Transform the climate normals to standard form.
    units, normals = climatetransform.data_to_standard_units(units, normals, month)
    lon_arr, normals = climatetransform.normalize_longitudes(lon_arr, normals)

    output_fmt = get_output_fmt(output_file)

    if output_fmt in ('tiles', 'png', 'jpeg'):
        lat_arr, lon_arr, normals = climatetransform.pad_data(lat_arr, lon_arr, normals)
        lat_arr, normals = climatetransform.normalize_latitudes(lat_arr, normals)

    # Load normals to storage in the output format
    if output_fmt in ('png', 'jpeg'):
        projected_y_arr = climatetransform.lat2y(lat_arr)
        projected_x_arr = climatetransform.lon2x(lon_arr)
        climatetransform.save_contours(projected_y_arr, projected_x_arr, units, normals, output_file, month,
                                           length=8192,
                                           extent=(
                                               -climatetransform.EARTH_CIRCUMFERENCE/2,
                                               climatetransform.EARTH_CIRCUMFERENCE/2,
                                               -climatetransform.EARTH_CIRCUMFERENCE/2,
                                               climatetransform.EARTH_CIRCUMFERENCE/2
                                           ))

    elif output_fmt == 'tiles':
        projected_y_arr = climatetransform.lat2y(lat_arr)
        projected_x_arr = climatetransform.lon2x(lon_arr)
        climatetransform.save_contours_tiles(projected_y_arr, projected_x_arr, units, normals, output_file, month)

    elif output_fmt == 'db':
        climatetransform.save_db_data(
            lat_arr,
            lon_arr,
            units,
            normals,
            output_file,
            variable_name,
            start_time,
            end_time,
            month,
            data_source
        )

    else:
        raise Exception('Unexpected output format "%s"' % output_fmt)

    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
