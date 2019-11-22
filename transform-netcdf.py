#!/usr/bin/env python3
#
# Transforms NetCDF4 files to geoJSON files.
#
# Copyright (c) 2019 Carlos Torchia
#

import netCDF4
import sys
from datetime import timedelta
from datetime import datetime
import numpy as np
import json

def get_args(arguments):
    '''
    Determines command line arguments
    '''
    num_arguments = len(arguments)
    if num_arguments not in [6, 7]:
        print('Usage: ' + arguments[0] + ' <netcdf4-filename> <geojson-filename> <var> <start-year> <end-year> [month]', file=sys.stderr)

    nc_file = arguments[1]
    geojson_file = arguments[2]
    variable_name = arguments[3]
    start_year = int(arguments[4])
    end_year = int(arguments[5])
    if num_arguments == 7:
        month = int(arguments[6])
        start_time = datetime(start_year, month, 1)
        end_time = datetime(end_year, month + 1, 1) - timedelta(seconds=1)
    else:
        month = 0
        start_time = datetime(start_year, 1, 1)
        end_time = datetime(end_year + 1, 1, 1) - timedelta(seconds=1)

    return (nc_file, geojson_file, variable_name, month, start_time, end_time)

def main(args):
    nc_file, geojson_file, variable_name, month, start_time, end_time = get_args(args)

    dataset = netCDF4.Dataset(nc_file)

    time_var = dataset.variables['time']
    lat_var = dataset.variables['lat']
    lon_var = dataset.variables['lon']
    value_var = dataset.variables[variable_name]

    normals = calculate_normals(time_var, lat_var, lon_var, value_var, start_time, end_time, month)
    geo_data = get_geo_data(lat_var, lon_var, value_var, normals, month)

    with open(geojson_file, 'w') as f:
        json.dump(geo_data, f, sort_keys=True, indent=4)

    return 0

def calculate_normals(time_var, lat_var, lon_var, value_var, start_time, end_time, month):
    '''
    Calculates the means (or totals) through the given time period.
    '''
    # Filter down the variables
    oldest_time = datetime.strptime(time_var.units, 'hours since %Y-%m-%d %H:%M:%S')
    start_delta = start_time - oldest_time
    end_delta = end_time - oldest_time
    start_hours = start_delta.days * 24
    end_hours = end_delta.days * 24

    # Determine the time indexes that correspond for this range and month
    time_arr = time_var[:]
    time_indexes_range = np.where((time_arr >= start_hours) & (time_arr <= end_hours))[0]

    if month:
        filtered_time_indexes = []
        for time_i in time_indexes_range:
            time_value = time_var[time_i]
            time = oldest_time + timedelta(hours=time_value)
            if time.month == month:
                filtered_time_indexes.append(time_i)
    else:
        filtered_time_indexes = time_indexes_range

    # Filter the data by the time indexes
    values = value_var[:]
    filtered_values = values[filtered_time_indexes, :, :]

    # Compute the means (or totals) of each coordinate through time axis
    if (value_var.name == 'precip' and not month):
        totals = filtered_values.sum(axis = 0) / ((end_time - start_time).days / 365)
        return totals
    else:
        means = filtered_values.mean(axis = 0)
        return means

def get_geo_data(lat_var, lon_var, value_var, data_arr, month):
    '''
    Gives the geoJSON for the specified data.
    For now, this gives one polygon per latitude. Plan is to create
    a polygon for each isometric set of contiguous coordinates.
    '''
    geo_data = []
    units = value_var.units
    for lat_i, data_for_lat in enumerate(data_arr):
        lat_value = lat_var[lat_i].item()
        for lon_i, value in enumerate(data_for_lat):
            lon_value = lon_var[lon_i].item()

            if not np.ma.is_masked(value):
                value = value.item()
                # Convert to standard units
                if units == 'degK':
                    new_value = value - 273.15
                    new_units = 'degC'
                elif units == 'cm':
                    new_value = value * 10.0
                    new_units = 'mm'
                else:
                    new_value = value
                    new_units = units

                if lon_value > 180:
                    lon_value -= 360

                feature = {
                    'type': 'Feature',
                    'properties': {
                        'name': '?',
                        'units': new_units,
                        'amount': round(new_value),
                        'month': month,
                        'comment': '',
                        'coordinates': [lon_value, lat_value]
                    },
                    'geometry': {
                        'type': 'Polygon',
                        'coordinates': [[
                            [lon_value - 0.25, lat_value + 0.25],
                            [lon_value - 0.25, lat_value - 0.25],
                            [lon_value + 0.25, lat_value - 0.25],
                            [lon_value + 0.25, lat_value + 0.25],
                            [lon_value - 0.25, lat_value + 0.25]
                        ]]
                    }
                }
                geo_data.append(feature)

    return geo_data

if __name__ == '__main__':
    sys.exit(main(sys.argv))
