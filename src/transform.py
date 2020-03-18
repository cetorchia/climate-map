#!/usr/bin/env python3
#
# Transforms datasets to various data formats for use
# as climate data by application.
#
# Copyright (c) 2020 Carlos Torchia
#
import os
import sys
from datetime import timedelta
from datetime import datetime
from datetime import date
import numpy as np
import math
import numbers
import netCDF4
from osgeo import gdal
import json
import stat
import re

import climatedb
from climatedb import NotFoundError

import arrays

# Constants
ALLOWED_GDAL_EXTENSIONS = ('tif', 'bil')
SECONDS_IN_A_DAY = 86400
AVERAGE_MONTH_DAYS = 30.436875
AVERAGE_FEB_DAYS = 28.2425

# Max latitude in OpenStreetMap, about 85.0511
# https://en.wikipedia.org/wiki/Web_Mercator_projection#Formulas
MAX_LAT = math.degrees(2*math.atan(math.exp(math.pi)) - math.pi/2)

def to_standard_variable_name(variable_name):
    '''
    Determines the standard variable name from the given variable name.
    This is useful when datasets use different variable names like "tmean" or "air"
    as we want to store everything under one variable name "tavg".
    This should be the same as the "measurements" table in the database
    and probably that table should have this information instead of
    here in this function.
    '''
    if variable_name in ('air', 'tmean', 'tas'):
        return 'tavg'

    elif variable_name == 'tasmin':
        return 'tmin'

    elif variable_name == 'tasmax':
        return 'tmax'

    elif variable_name in ('prec', 'pr', 'ppt'):
        return 'precip'

    elif variable_name == 'prsn':
        return 'snowfall'

    elif variable_name == 'sfcWind':
        return 'wind'

    else:
        return variable_name

def standard_units_from_measurement(measurement):
    '''
    Gives the standard units for a specified measurement.
    '''
    if measurement in ('tavg', 'tmin', 'tmax'):
        units = 'degC'
    elif measurement == 'precip':
        units = 'mm'
    else:
        raise Exception('Do not know standard units of %s' % measurement)

    new_value, standard_units = to_standard_units(0, units, 1)

    return standard_units

def units_from_filename(input_file):
    '''
    Determines the units of measurement for the specified filename.
    This is useful when the dataset does not contain the units, and we
    have to guess based on information in the filename.
    '''
    if re.search('tmax|tmin|tavg|tmean|tas', input_file):
        units = 'degC'
    elif input_file.find('prec') != -1:
        units = 'mm'
    else:
        raise Exception('Do not know the measurement units of ' + input_file)

    new_value, standard_units = to_standard_units(0, units, 1)

    return standard_units

def aggregate_normals(input_files, get_normals):
    '''
    Gives the average of the normals in each of the datasets.
    '''
    aggregated_normals = None

    for input_file in input_files:
        lat_arr, lon_arr, units, next_normals = get_normals(input_file)

        if aggregated_normals is None:
            aggregated_normals = next_normals
        else:
            aggregated_normals += next_normals

    number = len(input_files)
    return lat_arr, lon_arr, units, aggregated_normals / number

def normals_from_folder(input_folder, variable_name, month=0):
    '''
    Extracts climate normals from a folder. Usually, this will contain
    a series of GeoTIFF files, one for each month. Only the one with the month
    we want will be used, or all will be aggregated if month is 0.
    '''
    normals = None
    file_pattern = re.compile('([a-z]+)_?(\d+)\.(' + '|'.join(ALLOWED_GDAL_EXTENSIONS) + ')$')
    num_months = 0

    for filename in os.listdir(input_folder):
        input_file = os.path.join(input_folder, filename)
        mode = os.stat(input_file).st_mode

        if stat.S_ISREG(mode):
            match = file_pattern.search(input_file)

            if match:
                input_fmt = match.group(3)
                file_variable_name = to_standard_variable_name(match.group(1))

                if file_variable_name == to_standard_variable_name(variable_name):
                    if month == 0:
                        # Annual average
                        lat_arr, lon_arr, units, normals_for_month = normals_from_geotiff(input_file, input_fmt)

                        if normals is None:
                            normals = normals_for_month / 12
                        else:
                            normals += normals_for_month / 12

                        num_months += 1

                    else:
                        # Specific month
                        file_month = int(match.group(2))

                        if file_month == month:
                            return normals_from_geotiff(input_file, input_fmt)

    if normals is None and month:
        raise Exception('Could not find data for month %d in %s' % (month, input_folder))
    elif month == 0 and num_months < 12:
        raise Exception('Could not find data for all months in %s' % input_folder)

    return (lat_arr, lon_arr, units, normals)

def scale_array(data_arr, scale_factor=None, offset=None):
    '''
    This scales the array using the specified scale factor and offset.
    In the case of large datasets, we multiply by 10 to preserve
    one decimal and we convert to integers.
    '''
    if scale_factor is not None and scale_factor != 1:
        data_arr *= scale_factor

    if offset is not None:
        data_arr += offset * 10

    if isinstance(data_arr, np.ma.masked_array):
        if np.any(data_arr[~data_arr.mask] == data_arr.fill_value):
            raise Exception('Fill value is present in data after scaling')

    return data_arr

def normals_from_geotiff(input_file, input_fmt):
    '''
    Extracts climate normals from a GeoTIFF file.
    Returns a masked numpy array.
    '''
    if input_fmt not in ALLOWED_GDAL_EXTENSIONS:
        raise ValueError('Expected GeoTIFF file to end with "' + '" or "'.join(ALLOWED_GDAL_EXTENSIONS) + '"')

    dataset = gdal.Open(input_file)

    units = units_from_filename(input_file)

    if (dataset.RasterCount != 1):
        raise Exception('Expected 1 raster band, got ' + dataset.RasterCount)

    # We do not calculate the normals. Because the shape is two-dimensional, the
    # values can be assumed to be normals already.
    band = dataset.GetRasterBand(1)
    normals = band.ReadAsArray()

    if not isinstance(normals, np.ma.masked_array):
        normals = np.ma.masked_values(normals, band.GetNoDataValue())

    if input_fmt == 'bil' and units == 'degC':
        normals = scale_array(normals, 0.1)
    else:
        normals = scale_array(normals, band.GetScale(), band.GetOffset())

    if len(normals.shape) != 2:
        raise Exception('Expected two dimensional raster band, got ' + len(normals.shape))

    # Generate latitude and longitude arrays
    lon_start, lon_inc, x_skew, lat_start, y_skew, lat_inc = dataset.GetGeoTransform()
    if x_skew != 0:
        raise Exception('Expected Euclidean geometry, skew for longitude is ' + x_skew)
    if y_skew != 0:
        raise Exception('Expected Euclidean geometry, skew for latitude is ' + y_skew)

    lat_arr = np.linspace(lat_start, lat_start + (normals.shape[0] - 1) * lat_inc, normals.shape[0])
    lon_arr = np.linspace(lon_start, lon_start + (normals.shape[1] - 1) * lon_inc, normals.shape[1])

    return (lat_arr, lon_arr, units, normals)

def netcdf4_main_variable(dataset):
    '''
    Gives the name of the undimensional variable from a dataset.
    This is useful when you don't know for sure what the variable
    is called. It is probably the one variable that isn't a dimension.
    '''
    undimensional_variables = [var for name, var in dataset.variables.items() if name not in dataset.dimensions]

    if len(undimensional_variables) > 1:
        undimensional_variable_names = [var.name for var in undimensional_variables]
        raise Exception('Can\'t determine whether to use "' + '" or "'.join(undimensional_variable_names) + '"')
    elif len(undimensional_variables) == 0:
        raise Exception('No undimensional variables to use as variable')
    else:
        return undimensional_variables[0]

def normals_from_netcdf4(input_file, variable_name, start_time, end_time, month):
    '''
    Extracts climate normals from a NetCDF4 file.
    Returns a masked numpy array.
    '''
    dataset = netCDF4.Dataset(input_file)

    time_var = dataset.variables['time']
    lat_arr = dataset.variables['lat'][:]
    lon_arr = dataset.variables['lon'][:]

    if variable_name in dataset.variables:
        value_var = dataset.variables[variable_name]
    else:
        value_var = netcdf4_main_variable(dataset)
        print('Warning: variable %s not in %s, using "%s"' % (variable_name, input_file, value_var.name))

    if value_var.dtype is not value_var[0].dtype:
        print('Data type is wrong with netCDF4, opening with gdal')
        value_arr = gdal.Open(input_file).ReadAsArray()
    else:
        value_arr = value_var[:]

    units = value_var.units

    if not isinstance(value_arr, np.ma.masked_array):
        value_arr = np.ma.masked_values(value_arr, value_var.missing_value)

    normals = calculate_normals(time_var, value_arr, units, variable_name, start_time, end_time, month)

    scale_factor = value_var.scale_factor if hasattr(value_var, 'scale_factor') else None
    add_offset = value_var.add_offset if hasattr(value_var, 'add_offset') else None
    normals = scale_array(normals, scale_factor, add_offset)

    return (lat_arr, lon_arr, units, normals)

def calculate_normals(time_var, value_arr, units, variable_name, start_time, end_time, month):
    '''
    Calculates the means (or totals) through the given time period.
    '''
    # Parse the time units
    if time_var.size == 12:
        time_units = 'months'
    elif re.search('^hours since \d{4}-\d{2}-\d{2} \d{1,2}:\d{1,2}:\d{1,2}$', time_var.units):
        oldest_time = datetime.strptime(time_var.units, 'hours since %Y-%m-%d %H:%M:%S')
        time_units = 'hours'
    elif re.search('^days since \d{4}-\d{2}-\d{2} \d{1,2}:\d{1,2}:\d{1,2}\.\d{1,6}$', time_var.units):
        oldest_time = datetime.strptime(time_var.units, 'days since %Y-%m-%d %H:%M:%S.%f')
        time_units = 'days'
    elif re.search('^days since \d{4}-\d{2}-\d{2} \d{1,2}:\d{1,2}:\d{1,2}$', time_var.units):
        oldest_time = datetime.strptime(time_var.units, 'days since %Y-%m-%d %H:%M:%S')
        time_units = 'days'
    elif re.search('^days since \d{4}-\d{1,2}-\d{1,2}$', time_var.units):
        oldest_time = datetime.strptime(time_var.units, 'days since %Y-%m-%d')
        time_units = 'days'
    else:
        raise Exception('Don\'t understand the time units "%s"' % time_var.units)

    if time_units == 'months':
        #
        # In this case, the file only contains 12 time indexes,
        # so they are not actual moments in time and the data
        # is already aggregated by month.
        #
        if not month:
            filtered_time_indexes = np.arange(0, 12)
        else:
            filtered_time_indexes = np.array([month - 1])

    else:
        # Determine start and end times in the time units
        start_delta = start_time - oldest_time
        end_delta = end_time - oldest_time

        if time_units == 'hours':
            start = start_delta.days * 24
            end = end_delta.days * 24
            time_delta = lambda time_value: timedelta(hours=time_value)
        elif time_units == 'days':
            start = start_delta.days
            end = end_delta.days
            time_delta = lambda time_value: timedelta(days=time_value)
        else:
            raise Exception('Unexpected time units "%s"' % time_units)

        earliest_time = oldest_time + time_delta(time_var[0])
        if earliest_time.month != 1:
            print('Warning: Models that do not start in January (starting on %s) seem to contain errors sometimes. '
                  'Double check the output and make sure to calibrate.' % earliest_time,
                  file=sys.stderr)

        # Determine the time indexes that correspond for this range and month
        time_arr = time_var[:]
        time_indexes_range = np.where((time_arr >= start) & (time_arr <= end))[0]

        if month:
            filtered_time_indexes = []
            for time_i in time_indexes_range:
                time_value = time_var[time_i]
                time = oldest_time + time_delta(time_value)
                if time.month == month:
                    filtered_time_indexes.append(time_i)
        else:
            filtered_time_indexes = time_indexes_range

    # Filter the data by the time indexes
    filtered_values = value_arr[filtered_time_indexes, :, :]

    # Compute the average for each coordinate through time axis
    return filtered_values.mean(axis = 0)

def pad_data(lat_arr, lon_arr, data_arr):
    '''
    Augments the arrays with empty masked values in order to make
    the array big enough to fit in the 90 to -90 latitudes.
    This is particularly useful when the dataset does not include
    Antarctica, we still want the image to fit the bounds.
    '''
    # Don't pad the longitudes, but enforce it being 360
    lon_delta = lon_arr[1] - lon_arr[0]
    expected_lon_size = int((180 - (-180)) / abs(lon_delta))
    if lon_arr.size < expected_lon_size:
        raise Exception(
            'There should be %d longitudes if they have a delta of %g, found %d' % (
                expected_lon_size, lon_delta, lon_arr.size))

    # Determine the number of empty rows to add to the bottom.
    lat_delta = (lat_arr[lat_arr.size - 1] - lat_arr[0]) / (lat_arr.size - 1)
    if abs(lat_arr[0]) + abs(lat_delta) < 90:
        raise Exception('Expected first latitude to be within one delta of 90 or -90')
    desired_lat_size = int((90 - (-90)) / abs(lat_delta))
    if desired_lat_size < lat_arr.size:
        raise Exception(
            'Expected no more than %d latitudes (delta %g), found %d' % (desired_lat_size, abs(lat_delta), lat_arr.size)
        )
    aug_size = desired_lat_size - lat_arr.size

    # Pad the data array
    data_aug = np.full((aug_size, data_arr.shape[1]), data_arr.fill_value)
    new_data_arr = np.ma.append(data_arr, data_aug, axis=0)
    new_data_arr.set_fill_value(data_arr.fill_value)

    # Pad the latitudes too
    last_lat = lat_arr[lat_arr.size - 1]
    lat_aug = np.linspace(last_lat + lat_delta, last_lat + lat_delta * aug_size, aug_size)
    new_lat_arr = np.append(lat_arr, lat_aug)

    return new_lat_arr, lon_arr, new_data_arr

def normalize_longitudes(lon_arr, data_arr):
    '''
    Ensures that the longitudes start at -180. If they start at 0, for
    example, the longitudes starting at 180 will be moved to start at -180.
    Assumes axis 1 in the data array contains the longitudes.
    '''
    if not arrays.is_increasing(lon_arr):
        raise Exception('Longitudes are not strictly increasing')

    gt180_idxs = np.where(lon_arr >= 180)[0]

    if len(gt180_idxs) > 0:
        # Move the longitudes > 180 to the front, and then subtract 360
        lt180_idxs = np.where(lon_arr < 180)[0]
        new_lon_arr = np.append(lon_arr[gt180_idxs] - 360, lon_arr[lt180_idxs])
        new_data_arr = np.append(data_arr[:, gt180_idxs], data_arr[:, lt180_idxs], axis=1)
    else:
        new_lon_arr, new_data_arr = lon_arr, data_arr

    return new_lon_arr, new_data_arr

def normalize_latitudes(lat_arr, data_arr):
    '''
    Ensures that the latitudes go positive to negative. If they start
    at a negative number, they will be reversed and also the data will
    be reversed latitudinally.

    Assumes axis 0 in the data array contains the latitudes.
    '''
    if arrays.is_increasing(lat_arr):
        new_lat_arr, new_data_arr = lat_arr[::-1], data_arr[::-1]
    elif arrays.is_decreasing(lat_arr):
        new_lat_arr, new_data_arr = lat_arr, data_arr
    else:
        raise Exception('Latitudes are not strictly increasing or decreasing')

    return new_lat_arr, new_data_arr

def data_to_standard_units(units, data_arr, month):
    '''
    Converts the data array to standard units and gives the new units.
    '''
    new_data_arr, new_units = to_standard_units(data_arr, units, month)

    return new_units, new_data_arr

def days_in_month(month):
    '''
    Gives the number of days in the specified month.
    '''
    if month == 2:
        return AVERAGE_FEB_DAYS
    elif month == 0:
        # Average length of a month
        return AVERAGE_MONTH_DAYS
    else:
        return (date(2020 + month // 12, month % 12 + 1, 1) - date(2020, month, 1)).days

def to_standard_units(value, units, month):
    '''
    Gives the value in standard units
    Value can be a masked numpy array.
    '''
    if units in ('deg K', 'degK', 'K'):
        new_value = value - 273.15
        new_units = 'degC'
    elif units in ('deg C', 'C'):
        new_value = value
        new_units = 'degC'
    elif units == 'cm':
        new_value = value * 10
        new_units = 'mm'
    elif units == 'kg m-2 s-1':
        days = days_in_month(month)
        new_value = value * SECONDS_IN_A_DAY * days
        new_units = 'mm'
    else:
        new_value = value
        new_units = units

    return new_value, new_units
