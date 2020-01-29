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
import json
import climatetransform
import numpy as np

import climatedb

def get_args(arguments):
    '''
    Determines command line arguments
    '''
    num_arguments = len(arguments)
    if num_arguments not in [6, 7, 8]:
        print('Usage: ' + arguments[0] + ' <dataset-filename> <output-filename> <var> <start-year> <end-year> [month] [data-source]', file=sys.stderr)
        sys.exit(1)

    input_file = arguments[1]
    output_file = arguments[2]
    variable_name = arguments[3]
    start_year = int(arguments[4])
    end_year = int(arguments[5])

    if num_arguments >= 7:
        month = int(arguments[6])
        start_time = datetime(start_year, month, 1)
        # This will set the end time to the last second of the last day of the
        # specified month in the specified end year.
        # Credit to https://stackoverflow.com/a/4131114 for the div/mod by 12
        end_time = datetime(end_year + month // 12, month % 12 + 1, 1) - timedelta(seconds=1)

        if num_arguments >= 8:
            data_source = arguments[7]
        else:
            data_source = None
    else:
        month = 0
        start_time = datetime(start_year, 1, 1)
        end_time = datetime(end_year + 1, 1, 1) - timedelta(seconds=1)
        data_source = None

    # Determine input format
    if input_file.endswith(os.path.sep):
        input_fmt = 'folder'
    else:
        input_fmt = input_file.split('.')[-1]

        if input_fmt not in ('nc', 'tif', 'bil'):
            raise Exception('Unknown input format ' + input_fmt)

    # Determine output format
    if output_file.find(os.path.sep + 'tiles' + os.path.sep) != - 1 or output_file.startswith('tiles' + os.path.sep):
        output_fmt = 'tiles'
    elif output_file.endswith(os.path.sep):
        output_fmt = 'folder'
    elif climatedb.CONN_STR_RE.search(output_file):
        output_fmt = 'db'
        if data_source is None:
            raise Exception('Expected data source')
    else:
        output_fmt = output_file.split('.')[-1]

        if output_fmt not in ('json', 'png'):
            raise Exception('Unknown output format ' + output_fmt)

    return (input_file, input_fmt, output_file, output_fmt, variable_name, month, start_time, end_time, data_source)

def main(args):
    '''
    The main function
    '''
    input_file, input_fmt, output_file, output_fmt, variable_name, month, start_time, end_time, data_source = \
        get_args(args)

    # Extract and transform normals from dataset
    if input_fmt == 'nc':
        lat_arr, lon_arr, units, normals = climatetransform.normals_from_netcdf4(
            input_file,
            variable_name,
            start_time,
            end_time,
            month
        )

    elif input_fmt in ('tif', 'bil'):
        lat_arr, lon_arr, units, normals = climatetransform.normals_from_geotiff(input_file, input_fmt)

    elif input_fmt == 'folder':
        lat_arr, lon_arr, units, normals = climatetransform.normals_from_folder(input_file, variable_name, month)

    # Transform the climate normals to standard form.
    units, normals = climatetransform.data_to_standard_units(units, normals)

    if output_fmt in ('tiles', 'png'):
        lat_arr, lon_arr, normals = climatetransform.pad_data(lat_arr, lon_arr, normals)
        lon_arr, normals = climatetransform.normalize_longitudes(lon_arr, normals)
        lat_arr, normals = climatetransform.normalize_latitudes(lat_arr, normals)

    # Load normals to storage in the output format
    if output_fmt == 'json':
        data = climatetransform.get_data_dict(lat_arr, lon_arr, units, normals, month)

        with open(output_file, 'w') as f:
            json.dump(data, f)

    elif output_fmt == 'png':
        projected_lat_arr, projected_normals = climatetransform.project_data(lat_arr, normals)
        climatetransform.save_contours_png(projected_lat_arr, lon_arr, units, projected_normals, output_file, month)

    elif output_fmt == 'tiles':
        projected_lat_arr, projected_normals = climatetransform.project_data(lat_arr, normals)
        climatetransform.save_contours_tiles(projected_lat_arr, lon_arr, units, projected_normals, output_file, month)

    elif output_fmt == 'folder':
        climatetransform.save_folder_data(lat_arr, lon_arr, units, normals, output_file, variable_name, month)

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
