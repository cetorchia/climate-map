#!/usr/bin/env python3
#
# Transforms NetCDF4 files to various data formats for use
# as climate data.
#
# Copyright (c) 2019 Carlos Torchia
#
import os
import sys
dir_path = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'src')
sys.path.append(dir_path)

import netCDF4
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
        print('Usage: ' + arguments[0] + ' <netcdf4-filename> <output-filename> <var> <start-year> <end-year> [month]', file=sys.stderr)

    nc_file = arguments[1]
    output_file = arguments[2]
    variable_name = arguments[3]
    start_year = int(arguments[4])
    end_year = int(arguments[5])

    if num_arguments == 7:
        month = int(arguments[6])
        start_time = datetime(start_year, month, 1)
        # Credit to https://stackoverflow.com/a/4131114 for the div/mod by 12
        end_time = datetime(end_year + month // 12, month % 12 + 1, 1) - timedelta(seconds=1)
    else:
        month = 0
        start_time = datetime(start_year, 1, 1)
        end_time = datetime(end_year + 1, 1, 1) - timedelta(seconds=1)

    output_fmt = output_file.split('.')[-1]
    if output_fmt not in ('json', 'png'):
        raise Exception('Unknown output format ' + output_fmt)

    return (nc_file, output_file, output_fmt, variable_name, month, start_time, end_time)

def main(args):
    nc_file, output_file, output_fmt, variable_name, month, start_time, end_time = get_args(args)

    dataset = netCDF4.Dataset(nc_file)

    time_var = dataset.variables['time']
    lat_var = dataset.variables['lat']
    lon_var = dataset.variables['lon']
    value_var = dataset.variables[variable_name]

    normals = climatetransform.calculate_normals(time_var, lat_var, lon_var, value_var, start_time, end_time, month)

    if output_fmt == 'json':
        data = climatetransform.get_json_data(lat_var, lon_var, value_var, normals, month)

        with open(output_file, 'w') as f:
            json.dump(data, f)

    elif output_fmt == 'png':
        pixels = climatetransform.get_pixels(lat_var, lon_var, value_var, normals, month)
        png.from_array(pixels, 'RGB', info={
            'transparent': (0, 0, 0),
            'compression': 0,
        }).save(output_file)

    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
