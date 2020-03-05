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
import matplotlib.pyplot as plt
import cv2

import climatedb
from climatedb import NotFoundError

# Constants
ALLOWED_GDAL_EXTENSIONS = ('tif', 'bil')
TILE_LENGTH = 256
MAX_ZOOM_LEVEL = 7
ZOOM_LEVEL_OFFSET = 3
EARTH_RADIUS = 6378137
EARTH_CIRCUMFERENCE = 2 * math.pi * EARTH_RADIUS
SECONDS_IN_A_DAY = 86400
AVERAGE_MONTH_DAYS = 30.436875
AVERAGE_FEB_DAYS = 28.2425
SCALE_FACTOR = 10
ABSOLUTE_DIFFERENCE_MEASUREMENTS = 'tavg', 'tmin', 'tmax', 'precip'
OUTPUT_DTYPE = np.int16
OUTPUT_DTYPE_MIN = np.iinfo(OUTPUT_DTYPE).min
OUTPUT_DTYPE_MAX = np.iinfo(OUTPUT_DTYPE).max

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

def pack_array(data_arr, units=None):
    '''
    Masks the specified array with the specified missing value
    as a int16 array. If the numbers won't fit as int16, this
    will fail. Multiplies by 10 to not lose decimal points.
    '''
    if not isinstance(data_arr, np.ma.masked_array):
        raise Exception('Expected masked array in pack_array()')

    data_arr *= SCALE_FACTOR

    dtype = OUTPUT_DTYPE
    MIN_DTYPE = OUTPUT_DTYPE_MIN
    MAX_DTYPE = OUTPUT_DTYPE_MAX

    missing_value = data_arr.fill_value

    if np.any(data_arr.mask) and (missing_value < MIN_DTYPE or missing_value > MAX_DTYPE):
        new_missing_value = MIN_DTYPE

        if np.any(data_arr.base == new_missing_value):
            raise Exception('Data cannot contain %d as this is needed for missing values' % new_missing_value)

        np.place(data_arr.base, data_arr.mask, new_missing_value)
        data_arr.set_fill_value(new_missing_value)

        if np.any(data_arr.mask != (data_arr.base == new_missing_value)):
            raise Exception('Expected mask to all and only contain new missing value')

    if np.any((data_arr < MIN_DTYPE) | (data_arr > MAX_DTYPE)):
        raise Exception('Data contains values out of range (%d..%d) for a %s' % (MIN_DTYPE, MAX_DTYPE, dtype))

    return np.round(data_arr).astype(dtype)

def unpack_normals(normals):
    '''
    Divides each normal by 10.
    This would be done assuming all normals are stored as themselves
    multiplied by 10 in order to store them as an int16 and save space.
    '''
    new_normals = normals.copy()

    for measurement, measurement_normals in new_normals.items():
        if type(measurement_normals) is dict:
            for month, month_normals in measurement_normals.items():
                month_normals[0] /= SCALE_FACTOR

    return new_normals

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
    if not is_increasing(lon_arr):
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
    if is_increasing(lat_arr):
        new_lat_arr, new_data_arr = lat_arr[::-1], data_arr[::-1]
    elif is_decreasing(lat_arr):
        new_lat_arr, new_data_arr = lat_arr, data_arr
    else:
        raise Exception('Latitudes are not strictly increasing or decreasing')

    return new_lat_arr, new_data_arr

def is_increasing(arr):
    # See https://stackoverflow.com/a/4983359
    return all(x<y for x, y in zip(arr, arr[1:]))

def is_decreasing(arr):
    # See https://stackoverflow.com/a/4983359
    return all(x>y for x, y in zip(arr, arr[1:]))

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

def get_contour_levels(units):
    '''
    Returns a list of the contour levels for use with pyplot.contourf()
    '''
    if units == 'degC':
        return np.array([
            -40,
            -35,
            -30,
            -25,
            -20,
            -15,
            -10,
            -5,
            0,
            5,
            10,
            15,
            20,
            25,
            30,
            35,
            40,
        ]) * 10

    elif units == 'mm':
        return np.array([
            0,
            10,
            25,
            50,
            75,
            100,
            150,
            300,
            400,
            500,
        ]) * 10

    else:
        raise Exception('Unknown units: ' + units)

def get_contour_colours(levels, units):
    '''
    Returns a list of the contour colours for use with pyplot.contourf()
    '''
    return ['#%02X%02X%02X' % tuple(colour_for_amount(amount, units)) for amount in levels]

def colour_for_amount(amount, units):
    '''
    Returns the colour for the specified amount and units
    '''
    if units == 'degC':
        return degrees_celsius_colour(amount)

    elif units == 'mm':
        return precipitation_millimetres_colour(amount)

    else:
        raise Exception('Unknown units: ' + units)

def degrees_celsius_colour(amount):
    '''
    Returns the colour for the specified degrees Celsius.
    '''
    amount /= 10

    if amount >= 35:
        return 255, 0, 0
    elif amount >= 30:
        return 255, 34, 34
    elif amount >= 25:
        return 255, 68, 68
    elif amount >= 20:
        return 255, 102, 102
    elif amount >= 15:
        return 255, 136, 136
    elif amount >= 10:
        return 255, 170, 170
    elif amount >= 5:
        return 255, 204, 204
    elif amount >= 0:
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

def precipitation_millimetres_colour(amount):
    '''
    Returns the colour for the specified mm of precipitation.
    '''
    amount /= 10

    if amount >= 500:
        return 0, 0, 255
    elif amount >= 400:
        return 60, 60, 255
    elif amount >= 300:
        return 0, 255, 0
    elif amount >= 150:
        return 50, 255, 50
    elif amount >= 100:
        return 100, 255, 100
    elif amount >= 75:
        return 150, 255, 150
    elif amount >= 50:
        return 240, 255, 240
    elif amount >= 25:
        return 230, 230, 180
    elif amount >= 10:
        return 230, 230, 120
    else:
        return 240, 230, 90

def lat2y(lat):
    '''
    Converts the specified latitude to metres from the equator using
    the spherical Mercator projection.

    Accepts a numpy array, and the function will convert every value in the array.
    '''
    if isinstance(lat, numbers.Real) and lat == -90:
        return -lat2y(-lat)
    elif isinstance(lat, numbers.Real) and lat == 0:
        return 0
    else:
        # Source: https://wiki.openstreetmap.org/wiki/Mercator#Python_implementation
        return EARTH_RADIUS*np.log(np.tan(math.pi/4.0+np.radians(lat)/2.0))

def lon2x(lon):
    '''
    Converts the specified longitude to metres from the meridian using
    the spherical Mercator projection.

    Accepts a numpy array, and the function will convert every value in the array.
    '''
    # Source: https://wiki.openstreetmap.org/wiki/Mercator#Python_implementation
    return EARTH_RADIUS*np.radians(lon)

def save_contours_tiles(y_arr, x_arr, units, normals, output_folder, data_source_id):
    '''
    Saves contours in the data as PNG map tiles that will be displayable over
    the map. These tiles will use the same naming conventions/folder structure
    used by OpenStreetMap to not have to load the whole image. They will be stored
    as such in the specified output folder.

    E.g. /tiles/tavg-01/{z}/{x}/{y}.jpeg
    '''
    full_output_file = output_folder + '.png'
    os.makedirs(os.path.dirname(full_output_file), exist_ok=True)
    save_contours(y_arr, x_arr, units, normals, full_output_file, length=16384,
                      extent=(
                          -EARTH_CIRCUMFERENCE/2,
                          EARTH_CIRCUMFERENCE/2,
                          -EARTH_CIRCUMFERENCE/2,
                          EARTH_CIRCUMFERENCE/2
                      ))
    img = cv2.imread(full_output_file)

    max_zoom_level = MAX_ZOOM_LEVEL
    climatedb.update_max_zoom_level(data_source_id, max_zoom_level)
    climatedb.commit();

    for zoom_level in range(0, max_zoom_level + 1):
        print('Zoom level %d: ' % zoom_level, end='', flush=True)

        num_tiles = 2**zoom_level

        y_size = img.shape[0] / num_tiles
        x_size = img.shape[1] / num_tiles

        for y in range(0, num_tiles):
            y_start = int(round(y * y_size))
            y_end = int(round((y + 1) * y_size))
            img_y = img[y_start:y_end]

            for x in range(0, num_tiles):
                x_start = int(round(x * x_size))
                x_end = int(round((x + 1) * x_size))

                img_xy = img_y[:, x_start:x_end]
                if img_xy.shape[0] != img_y.shape[0]:
                    raise Exception('Unexpected mismatch of axis 0 on the img arrays')
                resized_img = cv2.resize(img_xy, (TILE_LENGTH, TILE_LENGTH), fx=0.5, fy=0.5, interpolation=cv2.INTER_CUBIC)

                output_parent = os.path.join(output_folder, str(zoom_level), str(x))
                os.makedirs(output_parent, exist_ok=True)
                output_file = os.path.join(output_parent, str(y) + '.jpeg')

                cv2.imwrite(output_file, resized_img)

            if y % math.ceil(num_tiles/100) == 0:
                print('.', end='', flush=True)

        print()

    os.remove(full_output_file)

def save_contours(y_arr, x_arr, units, normals, output_file, length=None, extent=None):
    '''
    Saves contours in the data as a PNG file that is displayable over
    the map.
    '''
    # Use dpi to ensure the plot takes up the expected dimensions in pixels.
    height = 1
    dpi = x_arr.size if length is None else length
    width = height

    fig = plt.figure()
    fig.set_size_inches(width, height)
    ax = plt.Axes(fig, [0, 0, width, height])
    if extent is not None:
        ax.set_xlim(extent[0], extent[1])
        ax.set_ylim(extent[2], extent[3])
    ax.set_axis_off()
    fig.add_axes(ax)

    contour_levels = get_contour_levels(units)
    contour_colours = get_contour_colours(contour_levels, units)

    cs = ax.contourf(x_arr, y_arr, normals, levels=contour_levels, colors=contour_colours, extend='both')
    cs.cmap.set_over(contour_colours[-1])
    cs.cmap.set_under(contour_colours[0])
    cs.changed()
    plt.savefig(output_file, dpi=dpi, transparent=True, quality=75)
    plt.close(fig)

def save_db_data(
        lat_arr,
        lon_arr,
        units,
        normals,
        variable_name,
        start_time,
        end_time,
        month,
        data_source,
        calibrated=False
):
    '''
    Saves the data into the specified database.
    '''
    measurement = to_standard_variable_name(variable_name)
    unit_id = climatedb.fetch_unit(units)['id']
    measurement_id = climatedb.fetch_measurement(measurement)['id']
    data_source_id = climatedb.fetch_data_source(data_source)['id']

    # Start date will vary by month, ensure entire year is saved
    start_date = date(start_time.year, 1, 1)
    end_date = date(end_time.year, 12, 31)

    lat_start = lat_arr[0].item()
    lat_delta = (lat_arr[lat_arr.size - 1] - lat_arr[0]) / (lat_arr.size - 1)
    lon_start = lon_arr[0].item()
    lon_delta = (lon_arr[lon_arr.size - 1] - lon_arr[0]) / (lon_arr.size - 1)

    fill_value = normals.fill_value

    try:
        dataset_record = climatedb.fetch_dataset(data_source_id, measurement_id, unit_id, start_date, end_date,
                                                 calibrated)

        tolerance = 10**-10

        if abs(lat_start - dataset_record['lat_start']) >= tolerance:
            raise Exception('Expected latitude start %0.11g to be the same as the existing %0.11g' % (
                lat_start, dataset_record['lat_start']
            ))

        if abs(lat_delta - dataset_record['lat_delta']) >= tolerance:
            raise Exception('Expected latitude delta %0.11g to be the same as the existing %0.11g' % (
                lat_delta, dataset_record['lat_delta']
            ))

        if abs(lon_start - dataset_record['lon_start']) >= tolerance:
            raise Exception('Expected longitude start %0.11g to be the same as the existing %0.11g' % (
                lon_start, dataset_record['lon_start']
            ))

        if abs(lon_delta - dataset_record['lon_delta']) >= tolerance:
            raise Exception('Expected longitude delta %0.11g to be the same as the existing %0.11g' % (
                lon_delta, dataset_record['lon_delta']
            ))

        if fill_value != dataset_record['fill_value']:
            raise Exception('Expected fill value %g to be the same as the existing %g' % (
                fill_value, dataset_record['fill_value']
            ))

        data_filename, lat_filename, lon_filename = climatedb.create_monthly_normals(
            data_source,
            start_date.year,
            end_date.year,
            measurement,
            units,
            lat_arr,
            lon_arr,
            normals,
            month,
            calibrated
        )

        if data_filename != dataset_record['data_filename']:
            raise Exception('Expected data filename "%s" to be the same as the existing "%s"' % (
                data_filename, dataset_record['data_filename']
            ))

        if lat_filename != dataset_record['lat_filename']:
            raise Exception('Expected latitude filename "%s" to be the same as the existing "%s"' % (
                data_filename, dataset_record['lat_filename']
            ))

        if lon_filename != dataset_record['lon_filename']:
            raise Exception('Expected longitude filename "%s" to be the same as the existing "%s"' % (
                data_filename, dataset_record['lon_filename']
            ))

        climatedb.commit()

    except NotFoundError:
        data_filename, lat_filename, lon_filename = climatedb.create_monthly_normals(
            data_source,
            start_date.year,
            end_date.year,
            measurement,
            units,
            lat_arr,
            lon_arr,
            normals,
            month,
            calibrated
        )

        climatedb.create_dataset(
            data_source_id,
            measurement_id,
            unit_id,
            start_date,
            end_date,
            lat_start,
            lat_delta,
            lon_start,
            lon_delta,
            fill_value,
            data_filename,
            lat_filename,
            lon_filename,
            calibrated
        )

        climatedb.commit()

def axis_limit_arrays(axis_arr, axis_delta):
    '''
    Returns left and right axis limit arrays. Each element provides
    the limit that points in the range of the coordinate must fall right
    and left of which respectively.
    '''
    left_axis_limit = axis_arr[0] - axis_delta / 2
    right_axis_limit = axis_arr[-1] + axis_delta / 2

    left_axis_limit_arr = np.empty(axis_arr.size)
    left_axis_limit_arr[0] = left_axis_limit
    left_axis_limit_arr[1:] = (axis_arr[:-1] + axis_arr[1:]) / 2

    right_axis_limit_arr = np.empty(axis_arr.size)
    right_axis_limit_arr[:-1] = (axis_arr[:-1] + axis_arr[1:]) / 2
    right_axis_limit_arr[-1] = right_axis_limit

    if axis_delta > 0:
        return left_axis_limit_arr, right_axis_limit_arr
    else:
        return right_axis_limit_arr, left_axis_limit_arr

def downscale_axis_arr(baseline_axis_arr, axis_arr, left_axis_limit_arr, right_axis_limit_arr):
    '''
    Downscales the lower resolution axis array to the higher resolution baseline axis array.
    '''
    axis_repeats = np.array([
        len(np.where(
            (baseline_axis_arr >= left_axis_limit) &
            (baseline_axis_arr < right_axis_limit)
        )[0])
        for left_axis_limit, right_axis_limit
        in zip(left_axis_limit_arr, right_axis_limit_arr)
    ])

    if left_axis_limit_arr[0] < left_axis_limit_arr[-1]:
        mask_left = len(np.where((baseline_axis_arr < left_axis_limit_arr[0]))[0])
        mask_right = len(np.where((baseline_axis_arr >= right_axis_limit_arr[-1]))[0])
    else:
        mask_left = len(np.where((baseline_axis_arr >= right_axis_limit_arr[0]))[0])
        mask_right = len(np.where((baseline_axis_arr < left_axis_limit_arr[-1]))[0])

    if axis_arr[-1] < axis_arr[0]:
        mask_left, mask_right = mask_right, mask_left

    if baseline_axis_arr.size != mask_left + axis_repeats.sum() + mask_right:
        raise Exception('Expected baseline axis to have size mask_left + axis_repeats + mask_right = %d' % (
                        mask_left + axis_repeats.sum() + mask_right))

    downscaled_axis_arr = np.ma.zeros(baseline_axis_arr.size)
    downscaled_axis_arr.mask = np.repeat(False, downscaled_axis_arr.size)
    downscaled_axis_arr.mask[:mask_left] = True
    downscaled_axis_arr.mask[-mask_right:] = True
    downscaled_axis_arr[mask_left:-mask_right] = np.repeat(axis_arr, axis_repeats)

    num_downscaled = np.nonzero(~downscaled_axis_arr.mask)[0].size

    if num_downscaled != axis_repeats.sum():
        raise Exception('Expected number %d of non-masked downscaled axis elements to be %d' % (
            num_downscaled, axis_repeats.sum()))

    return mask_left, mask_right, downscaled_axis_arr, axis_repeats

def check_downscaled_axis_arr(
        baseline_axis_arr,
        downscaled_axis_arr,
        left_axis_limit_arr,
        right_axis_limit_arr,
        axis_repeats
):
    '''
    Checks that the downscaled axis array corresponds to the each coordinate
    in the baseline. Throws an exception if not.
    '''
    downscaled_left_axis_limit_arr = np.ma.empty_like(downscaled_axis_arr)
    downscaled_left_axis_limit_arr.mask = downscaled_axis_arr.mask.copy()
    downscaled_left_axis_limit_arr[~downscaled_axis_arr.mask] = np.repeat(left_axis_limit_arr, axis_repeats)

    downscaled_right_axis_limit_arr = np.ma.empty_like(downscaled_axis_arr)
    downscaled_right_axis_limit_arr.mask = downscaled_axis_arr.mask.copy()
    downscaled_right_axis_limit_arr[~downscaled_axis_arr.mask] = np.repeat(right_axis_limit_arr, axis_repeats)

    invalid_baseline_coordinates = (
        (baseline_axis_arr < downscaled_left_axis_limit_arr) |
        (baseline_axis_arr >= downscaled_right_axis_limit_arr)
    )

    if np.any(invalid_baseline_coordinates):
        raise Exception('Baseline coordinates %a out of bounds for downscaled %a' % (
            baseline_axis_arr[invalid_baseline_coordinates],
            downscaled_axis_arr[invalid_baseline_coordinates]
        ))

    invalid_downscaled_coordinates = (
        (downscaled_axis_arr < downscaled_left_axis_limit_arr) |
        (downscaled_axis_arr >= downscaled_right_axis_limit_arr)
    )

    if np.any(invalid_downscaled_coordinates):
        raise Exception('Downscaled coordinates %a out of bounds for %a,%a' % (
            downscaled_axis_arr[invalid_downscaled_coordinates],
            downscaled_left_axis_limit_arr[invalid_downscaled_coordinates],
            downscaled_right_axis_limit_arr[invalid_downscaled_coordinates]
        ))

def downscale_array(baseline_lat_arr, baseline_lon_arr, lat_arr, lat_delta, lon_arr, lon_delta, data_arr):
    '''
    Downscales the lower-resolution data to the specified higher-resolution baseline data.
    '''
    baseline_lat_increasing = is_increasing(baseline_lat_arr)
    baseline_lat_decreasing = is_decreasing(baseline_lat_arr)

    if not baseline_lat_decreasing and not baseline_lat_increasing:
        raise Exception('Expected baseline latitudes to be increasing or decreasing')

    baseline_lon_increasing = is_increasing(baseline_lon_arr)
    baseline_lon_decreasing = is_decreasing(baseline_lon_arr)

    if not baseline_lon_decreasing and not baseline_lon_increasing:
        raise Exception('Expected baseline longitudes to be increasing or decreasing')

    lat_increasing = is_increasing(lat_arr)
    lat_decreasing = is_decreasing(lat_arr)

    if not lat_decreasing and not lat_increasing:
        raise Exception('Expected latitudes to be increasing or decreasing')

    lon_increasing = is_increasing(lon_arr)
    lon_decreasing = is_decreasing(lon_arr)

    if not lon_decreasing and not lon_increasing:
        raise Exception('Expected longitudes to be increasing or decreasing')

    if (lat_increasing and baseline_lat_decreasing) \
    or (lat_decreasing and baseline_lat_increasing):
        lat_arr = lat_arr[::-1]
        lat_delta = -lat_delta
        data_arr = data_arr[::-1]

    if (lon_increasing and baseline_lon_decreasing) \
    or (lon_decreasing and baseline_lon_increasing):
        lon_arr = lon_arr[::-1]
        lon_delta = -lon_delta
        data_arr = data_arr[:, ::-1]

    left_lat_limit_arr, right_lat_limit_arr = axis_limit_arrays(lat_arr, lat_delta)
    lat_mask_left, lat_mask_right, downscaled_lat_arr, lat_repeats = downscale_axis_arr(baseline_lat_arr, lat_arr,
                                                                                        left_lat_limit_arr,
                                                                                        right_lat_limit_arr)

    left_lon_limit_arr, right_lon_limit_arr = axis_limit_arrays(lon_arr, lon_delta)
    lon_mask_left, lon_mask_right, downscaled_lon_arr, lon_repeats = downscale_axis_arr(baseline_lon_arr, lon_arr,
                                                                                        left_lon_limit_arr,
                                                                                        right_lon_limit_arr)

    check_downscaled_axis_arr(baseline_lat_arr, downscaled_lat_arr,
                              left_lat_limit_arr, right_lat_limit_arr, lat_repeats)
    check_downscaled_axis_arr(baseline_lon_arr, downscaled_lon_arr,
                              left_lon_limit_arr, right_lon_limit_arr, lon_repeats)

    downscaled_data_arr = np.ma.empty((downscaled_lat_arr.size, downscaled_lon_arr.size))
    downscaled_data_arr.mask = np.repeat(False, downscaled_data_arr.size).reshape(downscaled_data_arr.shape)
    downscaled_data_arr.set_fill_value(
        data_arr.fill_value if isinstance(data_arr, np.ma.masked_array) else OUTPUT_DTYPE_MIN
    )

    downscaled_data_arr.mask[downscaled_lat_arr.mask, :] = True
    downscaled_data_arr.base[downscaled_lat_arr.mask, :] = downscaled_data_arr.fill_value
    downscaled_data_arr.mask[:, downscaled_lon_arr.mask] = True
    downscaled_data_arr.base[:, downscaled_lon_arr.mask] = downscaled_data_arr.fill_value

    downscaled_data_subarr = np.repeat(data_arr, lat_repeats, axis=0)
    downscaled_data_subarr = np.repeat(downscaled_data_subarr, lon_repeats, axis=1)

    downscaled_data_arr[lat_mask_left:-lat_mask_right, lon_mask_left:-lon_mask_right] = downscaled_data_subarr

    return downscaled_data_arr

def calibrate(
        baseline_data_source_code,
        historical_data_source_code,
        projection_data_source_code,
        measurement,
        units,
        baseline_start_date,
        baseline_end_date,
        projection_start_date,
        projection_end_date,
        month
):
    '''
    Adds projected differences to the baseline data.
    '''
    unit_id = climatedb.fetch_unit(units)['id']
    measurement_id = climatedb.fetch_measurement(measurement)['id']

    baseline_data_source = climatedb.fetch_data_source(baseline_data_source_code)
    if not baseline_data_source['baseline']:
        raise Exception('Expected data source %s to be flagged as "baseline"' % baseline_data_source_code)

    historical_data_source = climatedb.fetch_data_source(historical_data_source_code)
    projection_data_source = climatedb.fetch_data_source(projection_data_source_code)

    print('Using historical dataset %s-%d-%d-%s-%s' % (
        historical_data_source_code,
        baseline_start_date.year,
        baseline_end_date.year,
        measurement,
        units
    ))
    historical_dataset = climatedb.fetch_dataset(
        historical_data_source['id'],
        measurement_id,
        unit_id,
        baseline_start_date,
        baseline_end_date,
        calibrated=False
    )
    historical_lat, historical_lon, historical_data = climatedb.fetch_normals_from_dataset(historical_dataset, month)

    print('And projection dataset %s-%d-%d-%s-%s' % (
        projection_data_source_code,
        projection_start_date.year,
        projection_end_date.year,
        measurement,
        units
    ))
    projection_dataset = climatedb.fetch_dataset(
        projection_data_source['id'],
        measurement_id,
        unit_id,
        projection_start_date,
        projection_end_date,
        calibrated=False
    )
    projection_lat, projection_lon, projection_data = climatedb.fetch_normals_from_dataset(projection_dataset, month)

    if projection_data.shape != historical_data.shape:
        raise Exception('Expected historical data to have the same shape as projection')

    if np.any(projection_lat != historical_lat):
        raise Exception('Expected historical latitudes to be the same as projection latitudes')

    if np.any(projection_lon != historical_lon):
        raise Exception('Expected historical longitudes to be the same as projection longitudes')

    if measurement in ABSOLUTE_DIFFERENCE_MEASUREMENTS:
        print('Using absolute difference')
        differences = np.float64(projection_data) - np.float64(historical_data)
    else:
        print('Using relative difference')
        differences = projection_data / historical_data

    print('Against baseline dataset %s-%d-%d-%s-%s' % (
        baseline_data_source_code,
        baseline_start_date.year,
        baseline_end_date.year,
        measurement,
        units
    ))
    baseline_dataset = climatedb.fetch_dataset(
        baseline_data_source['id'],
        measurement_id,
        unit_id,
        baseline_start_date,
        baseline_end_date,
        calibrated=False
    )
    baseline_lat, baseline_lon, baseline_data = climatedb.fetch_normals_from_dataset(baseline_dataset, month)

    downscaled_differences = downscale_array(
        baseline_lat,
        baseline_lon,
        projection_lat,
        projection_dataset['lat_delta'],
        projection_lon,
        projection_dataset['lon_delta'],
        differences
    )

    if downscaled_differences.shape != baseline_data.shape:
        raise Exception('Expected downscaled differences to have the same shape as baseline data')

    if measurement in ABSOLUTE_DIFFERENCE_MEASUREMENTS:
        calibrated_data = np.float64(baseline_data) + downscaled_differences
    else:
        calibrated_data = np.round(baseline_data * downscaled_differences)

    if np.any(calibrated_data > OUTPUT_DTYPE_MAX):
        raise Exception('Calibrated data is out of bounds for %s' % OUTPUT_DTYPE)
    else:
        calibrated_data = calibrated_data.astype(OUTPUT_DTYPE)

    save_db_data(
        baseline_lat,
        baseline_lon,
        units,
        calibrated_data,
        measurement,
        projection_start_date,
        projection_end_date,
        month,
        projection_data_source['code'],
        calibrated=True
    )

    print('Created calibrated dataset %s-%d-%d-%s-%s-calibrated' % (
        projection_data_source_code,
        projection_start_date.year,
        projection_end_date.year,
        measurement,
        units
    ))

def calibrate_location(dataset, lat, lon):
    '''
    Calibrates the climate normals at a specific location
    against historical data.
    '''
    measurement = climatedb.fetch_measurement_by_id(dataset['measurement_id'])['code']
    baseline_data_source_id = climatedb.fetch_baseline_data_source()
    baseline_start_date, baseline_end_date = list(climatedb.fetch_date_ranges_by_data_source_id(baseline_data_source_id))[0]
    baseline_dataset = climatedb.fetch_dataset(
        baseline_data_source_id,
        dataset['measurement_id'],
        dataset['unit_id'],
        baseline_start_date,
        baseline_end_date,
        calibrated=False
    )

    historical_data_source_id = climatedb.fetch_historical_data_source(dataset['data_source_id'])
    historical_dataset = climatedb.fetch_dataset(
        historical_data_source_id,
        dataset['measurement_id'],
        dataset['unit_id'],
        baseline_start_date,
        baseline_end_date,
        calibrated=False
    )

    projection_dataset = climatedb.fetch_dataset(
        dataset['data_source_id'],
        dataset['measurement_id'],
        dataset['unit_id'],
        dataset['start_date'],
        dataset['end_date'],
        calibrated=False
    )

    actual_lat, actual_lon, historical_normals_arr = climatedb.fetch_monthly_normals(historical_dataset, lat, lon)
    actual_lat, actual_lon, projection_normals_arr = climatedb.fetch_monthly_normals(projection_dataset, lat, lon)
    actual_lat, actual_lon, baseline_normals_arr = climatedb.fetch_monthly_normals(baseline_dataset, lat, lon)

    if measurement in ABSOLUTE_DIFFERENCE_MEASUREMENTS:
        normals_arr = np.float64(baseline_normals_arr) + np.float64(projection_normals_arr) - np.float64(historical_normals_arr)
    else:
        normals_arr = np.float64(baseline_normals_arr) * np.float64(projection_normals_arr) / np.float64(historical_normals_arr)

    return actual_lat, actual_lon, normals_arr

def load_geonames(filename):
    '''
    Loads the geonames from the specified file.
    See https://download.geonames.org/export/dump/ for export and documentation.
    '''
    with open(filename, encoding='utf-8') as f:
        climatedb.delete_geonames()
        for line in f:
            row = line[:-1].split('\t')
            (
                geonameid,
                name,
                asciiname,
                alternatenames,
                latitude,
                longitude,
                feature_class,
                feature_code,
                country,
                cc2,
                admin1_code,
                admin2_code,
                admin3_code,
                admin4_code,
                population,
                elevation,
                dem,
                timezone,
                modification_date,
            ) = row

            population = None if population == '' else int(population)
            elevation = None if elevation == '' else int(elevation)

            climatedb.create_geoname(
                geonameid,
                name,
                latitude,
                longitude,
                country,
                population,
                elevation
            )

    climatedb.commit()
