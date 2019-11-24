#!/usr/bin/env python3
#
# Transforms NetCDF4 files to various data formats for use
# as climate data.
#
# Copyright (c) 2019 Carlos Torchia
#
from datetime import timedelta
from datetime import datetime
import numpy as np

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

def to_standard_units(value, units):
    '''
    Gives the value in standard units
    '''
    if units == 'degK':
        new_value = value - 273.15
        new_units = 'degC'
    elif units == 'cm':
        new_value = value * 10.0
        new_units = 'mm'
    else:
        new_value = value
        new_units = units

    return new_value, new_units

def get_geojson_data(lat_var, lon_var, value_var, data_arr, month):
    '''
    Gives the geoJSON for the specified data.
    '''
    geojson_data = []
    units = value_var.units
    for lat_i, data_for_lat in enumerate(data_arr):
        lat_value = lat_var[lat_i].item()
        for lon_i, value in enumerate(data_for_lat):
            lon_value = lon_var[lon_i].item()

            if not np.ma.is_masked(value):
                value = value.item()
                new_value, new_units = to_standard_units(value, units)

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
                        'type': 'Point',
                        'coordinates': [lon_value, lat_value]
                    }
                }
                geojson_data.append(feature)

    return geojson_data

def get_png_data(lat_var, lon_var, value_var, data_arr):
    '''
    Gives the PNG representation of the specified data.
    '''
    png_data = []
    units = value_var.units
    for lat_i, data_for_lat in enumerate(data_arr):
        lat_value = lat_var[lat_i].item()
        for lon_i, value in enumerate(data_for_lat):
            lon_value = lon_var[lon_i].item()

            if not np.ma.is_masked(value):
                value = value.item()
                new_value, new_units = to_standard_units(value, units)

                if lon_value > 180:
                    lon_value -= 360

                red = 0
                green = 0
                blue = 0
                png_data.append(red)
                png_data.append(green)
                png_data.append(blue)

    return png_data
