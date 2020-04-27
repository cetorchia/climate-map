#!/usr/bin/env python3
#
# Loads a dataset into a variable without attaching it
# to a date range. This is useful when the dataset is
# not expected to change significantly over time, for example
# elevation.
#
# For monthly climate normals such as temperature and precipitation,
# please use transform-dataset.py.
#
# Copyright (c) 2020 Carlos Torchia
#
import os
import sys
_dir_path = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'src')
sys.path.append(_dir_path)

import transform
import climatedb

def get_args(arguments):
    '''
    Determines command line arguments
    '''
    num_arguments = len(arguments)

    if num_arguments < 4 or num_arguments > 5:
        print('Usage: ' + arguments[0] + ' [options] <dataset-filename1> <var> <data-source>', file=sys.stderr)
        print('\nThis is for non-temporal datasets only.', file=sys.stderr)
        print('For monthly climate normals please use transform-dataset.py', file=sys.stderr)
        print('\nOptions:', file=sys.stderr)
        print('--ignore-scale-factor    Ignores the scale factor specified in netCDF4 dataset', file=sys.stderr)
        sys.exit(1)

    ignore_scale_factor = ('--ignore-scale-factor' in arguments[1:-3])

    input_file, variable_name, data_source = arguments[-3:]

    return input_file, variable_name, data_source, ignore_scale_factor

def get_input_fmt(input_file):
    '''
    Gives the format of the specified input file.
    '''
    input_fmt = input_file.split('.')[-1]

    if input_fmt not in ('nc', 'tif', 'bil'):
        raise Exception('Unsupported input format ' + input_fmt)

    return input_fmt

def get_data_from_file(input_file, variable_name, ignore_scale_factor):
    '''
    Retrieves data from the specified file.
    '''
    input_fmt = get_input_fmt(input_file)

    if input_fmt == 'nc':
        return transform.data_from_netcdf4(input_file, variable_name, ignore_scale_factor)

    elif input_fmt in ('tif', 'bil'):
        return transform.normals_from_geotiff(input_file, input_fmt)

    else:
        raise Exception('Unexpected input format "%s"' % input_fmt)

def main(args):
    '''
    The main function
    '''
    input_file, variable_name, data_source, ignore_scale_factor = get_args(args)

    print(variable_name, data_source)

    lat_arr, lon_arr, units, data_arr = get_data_from_file(input_file, variable_name, ignore_scale_factor)
    lon_arr, data_arr = transform.normalize_longitudes(lon_arr, data_arr)

    measurement = transform.to_standard_variable_name(variable_name)

    climatedb.connect()
    climatedb.save_nontemporal_data(lat_arr, lon_arr, units, data_arr, measurement, data_source)
    climatedb.close()

    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
