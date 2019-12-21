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
import png

def get_args(arguments):
    '''
    Determines command line arguments
    '''
    num_arguments = len(arguments)
    if num_arguments not in [6, 7]:
        print('Usage: ' + arguments[0] + ' <dataset-filename> <output-filename> <var> <start-year> <end-year> [month]', file=sys.stderr)
        sys.exit(1)

    input_file = arguments[1]
    output_file = arguments[2]
    variable_name = arguments[3]
    start_year = int(arguments[4])
    end_year = int(arguments[5])

    if num_arguments == 7:
        month = int(arguments[6])
        start_time = datetime(start_year, month, 1)
        # This will set the end time to the last second of the last day of the
        # specified month in the specified end year.
        # Credit to https://stackoverflow.com/a/4131114 for the div/mod by 12
        end_time = datetime(end_year + month // 12, month % 12 + 1, 1) - timedelta(seconds=1)
    else:
        month = 0
        start_time = datetime(start_year, 1, 1)
        end_time = datetime(end_year + 1, 1, 1) - timedelta(seconds=1)

    if input_file.endswith('/'):
        input_fmt = 'folder'
    else:
        input_fmt = input_file.split('.')[-1]

    if input_fmt not in ('nc', 'tif', 'folder'):
        raise Exception('Unknown input format ' + input_fmt)

    if output_file.endswith('/'):
        output_fmt = 'folder'
    else:
        output_fmt = output_file.split('.')[-1]

    if output_fmt not in ('json', 'png', 'folder'):
        raise Exception('Unknown output format ' + output_fmt)

    return (input_file, input_fmt, output_file, output_fmt, variable_name, month, start_time, end_time)

def main(args):
    '''
    The main function
    '''
    input_file, input_fmt, output_file, output_fmt, variable_name, month, start_time, end_time = get_args(args)

    # Extract and transform normals from dataset
    if input_fmt == 'nc':
        lat_arr, lon_arr, units, normals = climatetransform.normals_from_netcdf4(
            input_file,
            variable_name,
            start_time,
            end_time,
            month
        )

    elif input_fmt == 'tif':
        lat_arr, lon_arr, units, normals = climatetransform.normals_from_geotiff(input_file)

    elif input_fmt == 'folder':
        lat_arr, lon_arr, units, normals = climatetransform.normals_from_folder(input_file, variable_name, month)

    # Load normals to storage in the output format
    if output_fmt == 'json':
        data = climatetransform.get_data(lat_arr, lon_arr, units, normals, month)

        with open(output_file, 'w') as f:
            json.dump(data, f)

    elif output_fmt == 'png':
        pixels = climatetransform.get_pixels(lat_arr, lon_arr, units, normals, month)
        png.from_array(pixels, 'RGB', info={
            'transparent': (0, 0, 0),
            'compression': 9,
        }).save(output_file)

    elif output_fmt == 'folder':
        data = climatetransform.get_data(lat_arr, lon_arr, units, normals, month)
        climatetransform.save_folder_data(data, output_file, variable_name, month)

    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
