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
import math

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

def get_json_data(lat_var, lon_var, value_var, data_arr, month):
    '''
    Gives the JSON for the specified data.
    This data is indexed by latitude and longitude.
    '''
    data = {}
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

                if data.get(lat_value) is None:
                    data[lat_value] = {}

                data[lat_value][lon_value] = [
                    round(new_value),
                    new_units,
                ]

    return data

def get_pixels(lat_var, lon_var, value_var, data_arr, month):
    '''
    Gives the PNG representation of the specified data.
    '''
    units = value_var.units
    pixels = []
    y_pixels = 0

    for lat_i, data_for_lat in enumerate(data_arr):
        lat_value = lat_var[lat_i].item()

        if lat_value >= -85 and lat_value <= 85:
            begin_pixels = []
            end_pixels = []

            for lon_i, value in enumerate(data_for_lat):
                lon_value = lon_var[lon_i].item()

                if lon_value > 180:
                    row_pixels = begin_pixels
                else:
                    row_pixels = end_pixels

                if not np.ma.is_masked(value):
                    new_value, new_units = to_standard_units(value.item(), units)

                    red, green, blue = colour_for_amount(new_value, new_units, month)

                    row_pixels.append([red, green, blue])

                else:
                    row_pixels.append([0, 0, 0])

            height = pixels_for_latitude(lat_value, 0.5)
            row = begin_pixels + end_pixels
            rows = [row] * height
            pixels += rows

    return pixels

def colour_for_amount(amount, units, month):
    '''
    Returns the colour for the specified amount, units, and month.
    '''
    if units == 'degC':
        return degrees_celsius_colour(amount, month)

    elif units == 'mm':
        return precipitation_millimetres_colour(amount, month)

    else:
        raise Exception('Unknown units: ' + units)

def degrees_celsius_colour(amount, month):
    '''
    Returns the colour for the specified degrees Celsius.
    '''
    if not month:
        amount -= 10

    if amount > 35:
        return 255, 0, 0
    elif amount > 30:
        return 255, 34, 34
    elif amount > 25:
        return 255, 68, 68
    elif amount > 20:
        return 255, 102, 102
    elif amount > 15:
        return 255, 136, 136
    elif amount > 10:
        return 255, 170, 170
    elif amount > 5:
        return 255, 204, 204
    elif amount > 0:
        return 255, 238, 238
    elif amount < -35:
        return 0, 0, 255
    elif amount < -30:
        return 34, 34, 255
    elif amount < -25:
        return 68, 68, 255
    elif amount < -20:
        return 102, 102, 255
    elif amount < -15:
        return 136, 136, 255
    elif amount < -10:
        return 170, 170, 255
    elif amount < -5:
        return 204, 204, 255
    else:
        return 238, 238, 255

def precipitation_millimetres_colour(amount, month):
    '''
    Returns the colour for the specified mm of precipitation.
    '''
    if month:
        amount = amount * 12;

    if amount > 2000:
        return 68, 255, 68
    elif amount > 1000:
        return 136, 255, 136
    elif amount > 500:
        return 204, 255, 204
    elif amount < 100:
        return 255, 255, 68
    elif amount < 250:
        return 255, 255, 136
    else:
        return 255, 255, 204

def pixels_for_latitude(lat, size):
    '''
    Returns the number of pixels the latitude should take up based
    on the spherical Mercator projection. Size is the size of each
    point, in other words the distance between each latitude in the
    data.
    '''
    lat_north = lat + size / 2
    lat_south = lat - size / 2

    y_north = lat2y(lat_north)
    y_south = lat2y(lat_south)

    return round((y_north - y_south) * 10)

def lat2y(lat):
    '''
    Returns the Y projection of the specified latitude using
    the spherical Mercator projection.
    '''
    if lat < 0:
        return -lat2y(-lat)
    elif lat == 0:
        return 0

    return 180/math.pi*math.log(math.tan(math.pi/4.0+lat*(math.pi/180)/2.0))
