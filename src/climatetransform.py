#!/usr/bin/env python3
#
# Transforms datasets to various data formats for use
# as climate data by application.
#
# Copyright (c) 2019 Carlos Torchia
#
import os
from datetime import timedelta
from datetime import datetime
import numpy as np
import math
import netCDF4
from osgeo import gdal
import json
import stat

def normals_from_folder(input_folder, variable_name, month=0):
    '''
    Extracts climate normals from a folder. Usually, this will contain
    a series of GeoTIFF files, one for each month. The one with the month
    we want will be used only, or all will be aggregated if month is 0.
    '''
    normals = None

    for filename in os.listdir(input_folder):
        input_file = os.path.join(input_folder, filename)
        mode = os.stat(input_file).st_mode

        if stat.S_ISREG(mode) and input_file.endswith('.tif'):

            if month == 0:
                # Annual average/total, add up the normals.
                lat_arr, lon_arr, units, normals_for_file = normals_from_geotiff(input_file)

                if normals is None:
                    normals = normals_for_file
                else:
                    normals += normals_for_file

            else:
                # Specific month, is it the month?
                suffix = '_%02d.tif' % month

                if input_file.endswith(suffix):
                    return normals_from_geotiff(input_file)

    if normals is None:
        raise Exception('Could not find data for month %d in %s' % (month, input_folder))

    if variable_name != 'precip':
        normals /= 12

    return (lat_arr, lon_arr, units, normals)

def normals_from_geotiff(input_file):
    '''
    Extracts climate normals from a GeoTIFF file.
    Returns a masked numpy array.
    '''
    dataset = gdal.Open(input_file)

    if (dataset.RasterCount != 1):
        raise Exception('Expected 1 raster band, got ' + dataset.RasterCount)

    # We do not calculate the normals. Because the shape is two-dimensional, the
    # values can be assumed to be normals already.
    band = dataset.GetRasterBand(1)
    band_arr = band.ReadAsArray()
    normals = np.ma.masked_values(band_arr, band.GetNoDataValue())

    if len(normals.shape) != 2:
        raise Exception('Expected two dimensional raster band, got ' + len(normals.shape))

    # Generate latitude and longitude arrays
    lon_start, lon_inc, x_skew, lat_start, y_skew, lat_inc = dataset.GetGeoTransform()
    if x_skew != 0:
        raise Exception('Expected Euclidean geometry, skew for longitude is ' + x_skew)
    if y_skew != 0:
        raise Exception('Expected Euclidean geometry, skew for latitude is ' + y_skew)

    lat_arr = np.empty((normals.shape[0]))
    lat_arr[0] = lat_start
    for lat_i in range(1, lat_arr.size):
        lat_arr[lat_i] = lat_arr[lat_i - 1] + lat_inc

    lon_arr = np.empty((normals.shape[1]))
    lon_arr[0] = lon_start
    for lon_i in range(1, lon_arr.size):
        lon_arr[lon_i] = lon_arr[lon_i - 1] + lon_inc

    if input_file.find('tmax') != -1 or input_file.find('tmin') != -1 or input_file.find('tavg') != -1:
        units = 'degC'
    elif input_file.find('prec') != -1:
        units = 'mm'
    else:
        raise Exception('Do not know the measurement units of ' + input_file)

    return (lat_arr, lon_arr, units, normals)

def normals_from_netcdf4(input_file, variable_name, start_time, end_time, month):
    '''
    Extracts climate normals from a NetCDF4 file.
    Returns a masked numpy array.
    '''
    dataset = netCDF4.Dataset(input_file)

    time_var = dataset.variables['time']
    lat_arr = dataset.variables['lat'][:]
    lon_arr = dataset.variables['lon'][:]
    value_var = dataset.variables[variable_name]
    units = value_var.units

    normals = calculate_normals(time_var, value_var, variable_name, start_time, end_time, month)

    return (lat_arr, lon_arr, units, normals)

def calculate_normals(time_var, value_var, variable_name, start_time, end_time, month):
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
    if (variable_name == 'precip' and not month):
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

def get_data(lat_arr, lon_arr, units, data_arr, month):
    '''
    Gives the JSON for the specified data.
    This data is indexed by latitude and longitude.
    '''
    data = {}
    for lat_i, data_for_lat in enumerate(data_arr):
        lat_value = lat_arr[lat_i].item()
        for lon_i, value in enumerate(data_for_lat):
            lon_value = lon_arr[lon_i].item()

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

def get_pixels(lat_arr, lon_arr, units, data_arr, month):
    '''
    Gives the PNG representation of the specified data.
    '''
    pixels = []
    y_pixels = 0
    max_lat = 85 # Max latitude in OpenStreetMap
    y_total = data_arr.shape[0] # Total number of latitudes
    y_size = abs(lat_arr[1] - lat_arr[0])

    for lat_i, data_for_lat in enumerate(data_arr):
        lat_value = lat_arr[lat_i].item()

        if lat_value >= -max_lat and lat_value <= max_lat:
            begin_pixels = []
            end_pixels = []

            for lon_i, value in enumerate(data_for_lat):
                lon_value = lon_arr[lon_i].item()

                # Some data goes from 0 to 360 longitude, so we have to put
                # the 180 to 360 (equivalent to -180 to 0) at the beginning
                # as the map will start at -180.
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

            height = pixels_for_latitude(lat_value, y_size, y_pixels, max_lat, y_total)
            row = begin_pixels + end_pixels
            rows = [row] * height
            pixels += rows
            y_pixels += height

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

def pixels_for_latitude(lat, size, y_pixels, max_lat, y_total):
    '''
    Returns the number of pixels the latitude should take up based
    on the spherical Mercator projection. Size is the size of each
    point, in other words the distance between each latitude in the
    data.
    '''
    # For completeness we include the north latitude, but we are
    # basing the calculation on a running count of pixels so the
    # round off error balances out.
    lat_north = lat + size / 2 if lat < max_lat else max_lat
    lat_south = lat - size / 2 if lat > -max_lat else -max_lat

    # Scale to have enough pixels going top to bottom.
    # Scale the existing total pixels by the increase from the projection.
    y_max = lat2y(max_lat)
    new_total = (y_max / max_lat + 5) * y_total
    factor = new_total / y_max / 2

    y_north = y_max * factor - y_pixels
    y_south = lat2y(lat_south) * factor

    return round(y_north - y_south + 5)

def lat2y(lat):
    '''
    Returns the Y projection of the specified latitude using
    the spherical Mercator projection.
    '''
    if lat < 0:
        return -lat2y(-lat)
    elif lat == 0:
        return 0

    # Source: https://wiki.openstreetmap.org/wiki/Mercator#Python_implementation
    return 180/math.pi*math.log(math.tan(math.pi/4.0+lat*(math.pi/180)/2.0))

def save_folder_data(data, output_folder, variable_name, month):
    '''
    Saves data in coordinate folders for quick lookup of stats.
    Augments existing data.
    '''
    if variable_name == 'air':
        variable_name = 'tavg'

    if variable_name == 'prec':
        variable_name = 'precip'

    for lat_value in data:
        lat_index = str(math.floor(lat_value))
        lat_folder = os.path.join(output_folder, 'coords', lat_index)
        os.makedirs(lat_folder, exist_ok=True)

        for lon_value in data[lat_value]:
            lon_index = str(math.floor(lon_value))
            lon_folder = os.path.join(lat_folder, lon_index)
            if not os.path.exists(lon_folder):
                os.mkdir(lon_folder)

            coord_index = str(round(lat_value, 2)) + '_' + str(round(lon_value, 2))
            coord_file = os.path.join(lon_folder, coord_index + '.json')

            datum = data[lat_value][lon_value]

            if not os.path.exists(coord_file):
                existing_datum = {}
            else:
                with open(coord_file, 'r') as f:
                    existing_datum = json.load(f)

            if existing_datum.get(variable_name) is None:
                existing_datum[variable_name] = {}

            existing_datum[variable_name][month] = datum

            with open(coord_file, 'w') as f:
                json.dump(existing_datum, f)
