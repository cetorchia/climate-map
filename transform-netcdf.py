#!/usr/bin/env python3
#
# Transforms NetCDF4 files to geoJSON files.
#

import netCDF4
import sys
from datetime import timedelta
from datetime import datetime
import numpy as np

def get_args(arguments):
    '''
    Determines command line arguments
    '''
    if len(arguments) != 7:
        print('Usage: ' + arguments[0] + ' <netcdf4-filename> <geojson-filename> <var> <start-year> <end-year> <month>', file=sys.stderr)

    nc_file = arguments[1]
    geojson_file = arguments[2]
    variable_name = arguments[3]
    start_year = int(arguments[4])
    end_year = int(arguments[5])
    month = int(arguments[6])

    start_time = datetime(start_year, month, 1)
    end_time = datetime(end_year, month + 1, 1) - timedelta(seconds=1)

    return (nc_file, geojson_file, variable_name, month, start_time, end_time)

def main(args):
    nc_file, geojson_file, variable_name, month, start_time, end_time = get_args(args)

    dataset = netCDF4.Dataset(nc_file)

    time_var = dataset.variables['time']
    lat_var = dataset.variables['lat']
    lon_var = dataset.variables['lon']
    value_var = dataset.variables[variable_name]

    oldest_time = datetime.strptime(time_var.units, 'hours since %Y-%m-%d %H:%M:%S')
    start_delta = start_time - oldest_time
    end_delta = end_time - oldest_time

    start_hours = start_delta.days * 24
    end_hours = end_delta.days * 24

    new_arr = analyze_dataset(time_var, lat_var, lon_var, value_var, start_hours, end_hours, month, oldest_time)

def analyze_dataset(time_var, lat_var, lon_var, value_var, start_hours, end_hours, month, oldest_time):
    '''
    Loop through data
    '''
    # Filter down the variables
    time_arr = time_var[:]
    filtered_time = np.where((time_arr >= start_hours) & (time_arr <= end_hours))[0]

    new_arr = np.ma.array(np.ndarray((lat_var.size, lon_var.size)))

    for lat_i in range(lat_var.size):
        lat_value = lat_var[lat_i]
        for lon_i in range(lon_var.size):
            lon_value = lon_var[lon_i]
            if value_var[0][lat_i][lon_i] != np.ma.core.MaskedConstant:
                value_sum = 0.0
                value_num = 0

                for time_i in filtered_time:
                    time_value = time_var[time_i]
                    time = oldest_time + timedelta(hours=time_value)
                    if time.month == month:
                        value = value_var[time_i][lat_i][lon_i]

                        if value != np.ma.core.MaskedConstant:
                            value_num += 1
                            value_sum += value

                if (value_num > 0):
                    mean_value = value_sum / value_num
                    new_arr[lat_i][lon_i] = mean_value

                    print('Latitude:', lat_value)
                    print('Longitude:', lon_value)
                    print(value_var.long_name + ':', mean_value)
                    print('---')
                else:
                    new_arr[lat_i][lon_i] = np.ma.masked

    return new_arr

main(sys.argv)
