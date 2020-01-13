#!/usr/bin/env python3
#
# Transforms datasets to various data formats for use
# as climate data by application.
#
# Copyright (c) 2019 Carlos Torchia
#
import os
import sys
from datetime import timedelta
from datetime import datetime
import numpy as np
import math
import netCDF4
from osgeo import gdal
import json
import stat
import re
import png
import matplotlib.pyplot as plt
import cv2

# Constants
ALLOWED_GDAL_EXTENSIONS = ('tif', 'bil')
TILE_LENGTH = 256
MAX_ZOOM_LEVELS = 10

# Max latitude in OpenStreetMap, about 85.0511
# https://en.wikipedia.org/wiki/Web_Mercator_projection#Formulas
MAX_LAT = (2*math.atan(math.exp(math.pi)) - math.pi/2) * 180 / math.pi

def to_standard_variable_name(variable_name):
    '''
    Determines the standard variable name from the given variable name.
    This is useful when datasets use different variable names like "tmean" or "air"
    as we want to store everything under one variable name "tavg".
    '''
    if variable_name in ('air', 'tmean'):
        return 'tavg'

    elif variable_name == 'prec':
        return 'precip'

    else:
        return variable_name

def units_from_filename(input_file):
    '''
    Determines the units of measurement for the specified filename.
    This is useful when the dataset does not contain the units, and we
    have to guess based on information in the filename.
    '''
    if re.search('tmax|tmin|tavg|tmean', input_file):
        return 'degC'
    elif input_file.find('prec') != -1:
        return 'mm'
    else:
        raise Exception('Do not know the measurement units of ' + input_file)

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
                        # Annual average/total, add up the normals.
                        lat_arr, lon_arr, units, normals_for_file = normals_from_geotiff(input_file, input_fmt)

                        if normals is None:
                            normals = normals_for_file
                        else:
                            # Add the arrays of all months together.
                            normals += normals_for_file

                        num_months += 1

                    else:
                        # Specific month, is it the month?
                        file_month = int(match.group(2))

                        if file_month == month:
                            return normals_from_geotiff(input_file, input_fmt)

    if normals is None and month:
        raise Exception('Could not find data for month %d in %s' % (month, input_folder))
    elif month == 0 and num_months < 12:
        raise Exception('Could not find data for all months in %s' % input_folder)

    if variable_name != 'precip':
        normals /= 12

    return (lat_arr, lon_arr, units, normals)

def normals_from_geotiff(input_file, input_fmt):
    '''
    Extracts climate normals from a GeoTIFF file.
    Returns a masked numpy array.
    '''
    if input_fmt not in ALLOWED_GDAL_EXTENSIONS:
        raise ValueError('Expected GeoTIFF file to end with "' + '" or "'.join(ALLOWED_GDAL_EXTENSIONS) + '"')

    dataset = gdal.Open(input_file)

    units = units_from_filename(input_file)

    # The WorldClim v1 data multiplies temperatures by 10, because
    # the values are stored as integers and so they cannot have decimals.
    factor = 10 if input_fmt == 'bil' and units == 'degC' else 1

    if (dataset.RasterCount != 1):
        raise Exception('Expected 1 raster band, got ' + dataset.RasterCount)

    # We do not calculate the normals. Because the shape is two-dimensional, the
    # values can be assumed to be normals already.
    band = dataset.GetRasterBand(1)
    band_arr = band.ReadAsArray()
    normals = np.ma.masked_values(band_arr / factor, band.GetNoDataValue() / factor)

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

def pad_data(lat_arr, lon_arr, data_arr):
    '''
    Augments the arrays with empty masked values in order to make
    the array big enough to fit in the 90 to -90 latitudes.
    This is particularly useful when the dataset does not include
    Antarctica, we still want the image to fit the bounds.
    '''
    # Don't pad the longitudes, but enforce it being 360
    lon_delta = lon_arr[1] - lon_arr[0]
    expected_lon_size = int(round((180 - (-180)) / abs(lon_delta)))
    if lon_arr.size < expected_lon_size:
        raise Exception(
            'There should be %d longitudes if they have a delta of %g, found %d' % (
                expected_lon_size, lon_delta, lon_arr.size))

    # Just pad it on the bottom, not on the side.
    lat_delta = lat_arr[1] - lat_arr[0]
    if abs(lat_arr[0]) != 90:
        raise Exception('Expected first latitude to be 90')
    desired_lat_size = int(round((90 - (-90)) / abs(lat_delta)))
    aug_size = desired_lat_size - lat_arr.size
    if aug_size < 0:
        raise Exception('Expected no more than %d latitudes, found %d' % (desired_lat_size, lat_arr.size))

    data_aug = np.full((aug_size, data_arr.shape[1]), data_arr.fill_value)
    new_data_unmasked = np.append(data_arr, data_aug, axis=0)
    new_data_arr = np.ma.masked_values(new_data_unmasked, data_arr.fill_value)

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
    # Must be strictly increasing.
    # See https://stackoverflow.com/a/4983359
    if not all(x<y for x, y in zip(lon_arr, lon_arr[1:])):
        raise Exception('Longitudes are not strictly increasing')

    gt180_idxs = np.where(lon_arr > 180)[0]

    if len(gt180_idxs) > 0:
        # Move the longitudes > 180 to the front, and then subtract 360
        new_lon_arr = np.append(lon_arr[gt180_idxs] - 360, lon_arr[~gt180_idxs], axis=1)
        new_data_arr = np.append(data_arr[:, gt180_idxs], data_arr[:, ~gt180_idxs], axis=1)

        return new_lon_arr, new_data_arr
    else:
        return lon_arr, data_arr

def project_data(lat_arr, data_arr):
    '''
    Projects an array of climate data onto a sphere using the Mercator
    projection. This assumes the latitudes are along axis 0, i.e. data_arr[lat][lon].

    To do this, we multiply each row by how much space the latitude would take up
    on the projected map.

    We also return a new latitude array with each latitude multiplied to
    match the projected data.
    '''
    pixels_so_far = 0
    num_latitudes = data_arr.shape[0] # Total number of latitudes
    delta = abs(lat_arr[1] - lat_arr[0])
    repeats = np.empty(num_latitudes, np.int64)

    for lat_i in range(0, lat_arr.size):
        lat_value = lat_arr[lat_i].item()

        if lat_value >= -MAX_LAT and lat_value <= MAX_LAT:
            height = pixels_for_latitude(lat_value, delta, pixels_so_far, num_latitudes)
            repeats[lat_i] = height
            pixels_so_far += height

        else:
            repeats[lat_i] = 0

    projected_data_arr = np.repeat(data_arr, repeats, axis=0)
    projected_lat_arr = np.repeat(lat_arr, repeats, axis=0)

    return projected_lat_arr, projected_data_arr

def data_to_standard_units(units, data_arr):
    '''
    Converts the data array to standard units and gives the new units.
    '''
    new_data_arr = np.full(data_arr.shape, data_arr.fill_value)

    for lat_i in range(0, data_arr.shape[0]):
        for lon_i in range(0, data_arr.shape[1]):
            if not data_arr.mask[lat_i][lon_i]:
                value = data_arr[lat_i][lon_i]

                value = value.item()
                new_value, new_units = to_standard_units(value, units)

                new_data_arr[lat_i][lon_i] = new_value

    new_masked_arr = np.ma.masked_values(new_data_arr, data_arr.fill_value)
    return new_units, new_masked_arr

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

def get_data_dict(lat_arr, lon_arr, units, data_arr, month):
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

                if data.get(lat_value) is None:
                    data[lat_value] = {}

                data[lat_value][lon_value] = [
                    round(value, 1),
                    units,
                ]

    return data

def get_pixels(units, data_arr, month):
    '''
    Gives the PNG representation of the specified data.
    '''
    pixels = []

    for data_for_lat in data_arr:
        row = []

        for value in data_for_lat:

            if not np.ma.is_masked(value):
                red, green, blue = colour_for_amount(value, units, month)

                row.append([red, green, blue])

            else:
                row.append([0, 0, 0])

        pixels.append(row)

    return pixels

def get_contour_levels(units):
    '''
    Returns a list of the contour levels for use with pyplot.contourf()
    '''
    if units == 'degC':
        return [
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
        ]

    elif units == 'mm':
        return [
            0,
            100,
            250,
            500,
            1000,
            2000,
        ]

    else:
        raise Exception('Unknown units: ' + units)

def get_contour_colours(levels, units, month):
    '''
    Returns a list of the contour colours for use with pyplot.contourf()
    '''
    return ['#%02X%02X%02X' % tuple(colour_for_amount(amount, units, month)) for amount in levels]

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

def pixels_for_latitude(lat, delta, pixels_so_far, num_latitudes):
    '''
    Returns the number of pixels the latitude should take up based
    on the spherical Mercator projection. "Delta" is the size of each
    point, in other words the distance between each latitude in the
    data.
    '''
    # For completeness we include the north latitude, but we are
    # basing the calculation on a running count of pixels so the
    # round off error balances out.
    lat_north = min(lat + delta / 2, MAX_LAT) if lat < MAX_LAT else MAX_LAT
    lat_south = max(lat - delta / 2, -MAX_LAT) if lat > -MAX_LAT else -MAX_LAT

    # Scale to have enough pixels going top to bottom.
    # Scale the existing total pixels by the increase from the projection.
    # "Addition" gives the latitudes near the equator more pixels,
    # as this somehow makes the map line up better.
    addition = 1
    y_max = lat2y(MAX_LAT)
    new_total = (y_max / MAX_LAT + addition) * num_latitudes
    factor = new_total / y_max / 2

    y_north = y_max * factor - pixels_so_far
    y_south = lat2y(lat_south) * factor

    return round(y_north - y_south + addition)

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

def save_folder_data(lat_arr, lon_arr, units, data_arr, output_folder, variable_name, month):
    '''
    Saves data in coordinate folders for quick lookup of stats.
    Augments existing data.
    '''
    variable_name = to_standard_variable_name(variable_name)

    print('Storing data in folders: ', end='', flush=True)
    for lat_i, data_for_lat in enumerate(data_arr):
        lat_value = lat_arr[lat_i].item()
        lat_index = str(math.floor(lat_value))
        lat_folder = os.path.join(output_folder, 'coords', lat_index)
        os.makedirs(lat_folder, exist_ok=True)

        for lon_i, value in enumerate(data_for_lat):
            lon_value = lon_arr[lon_i].item()
            lon_index = str(math.floor(lon_value))
            lon_folder = os.path.join(lat_folder, lon_index)

            if not np.ma.is_masked(value):

                if not os.path.exists(lon_folder):
                    os.mkdir(lon_folder)

                coord_index = str(round(lat_value, 2)) + '_' + str(round(lon_value, 2))
                coord_file = os.path.join(lon_folder, coord_index + '.json')

                if not os.path.exists(coord_file):
                    existing_datum = {}
                else:
                    with open(coord_file, 'r') as f:
                        existing_datum = json.load(f)

                if existing_datum.get(variable_name) is None:
                    existing_datum[variable_name] = {}

                existing_datum[variable_name][month] = [round(value.item(), 1), units]

                with open(coord_file, 'w') as f:
                    json.dump(existing_datum, f)

        if lat_i % math.ceil(data_arr.shape[0] / 100) == 0:
            print('.', end='', flush=True)

    print()

def save_contours_tiles(lat_arr, lon_arr, units, normals, output_folder, month):
    '''
    Saves contours in the data as PNG map tiles that will be displayable over
    the map. These tiles will use the same naming conventions/folder structure
    used by OpenStreetMap to not have to load the whole image. They will be stored
    as such in the specified output folder.

    E.g. /tiles/temperature-avg-01/{z}/{x}/{y}.png
    '''
    max_zoom_levels = max(int(math.log2(lon_arr.size)), MAX_ZOOM_LEVELS)

    for zoom_level in range(0, max_zoom_levels):
        print('Zoom level %d: ' % zoom_level, end='', flush=True)

        num_tiles = 2**zoom_level
        lat_size = lat_arr.size / num_tiles
        lon_size = lon_arr.size / num_tiles

        lon_ranges = [(int(x * lon_size), int((x + 1) * lon_size)) for x in range(0, num_tiles)]
        sub_lon_arrs = [lon_arr[lon_i:lon_end] for lon_i, lon_end in lon_ranges]

        for y in range(0, num_tiles):
            lat_i = int(y * lat_size)
            lat_end = int((y + 1) * lat_size) #if y < num_tiles - 1 else lat_arr.size - 1 # really lat_end + 1

            sub_lat_arr = lat_arr[lat_i:lat_end]
            normals_for_lat_range = normals[lat_i:lat_end]

            for x in range(0, num_tiles):
                lon_i, lon_end = lon_ranges[x]
                #lon_end = lon_end if x < num_tiles - 1 else lon_arr.size - 1 # really lon_end + 1

                sub_lon_arr = sub_lon_arrs[x]
                sub_normals = normals_for_lat_range[:, lon_i:lon_end]

                output_parent = os.path.join(output_folder, str(zoom_level), str(x))
                os.makedirs(output_parent, exist_ok=True)
                output_file = os.path.join(output_parent, str(y) + '.png')

                if zoom_level <= max_zoom_levels:
                    save_contours_png(sub_lat_arr, sub_lon_arr, units, sub_normals, output_file, month, TILE_LENGTH)
                else:
                    save_png(sub_lat_arr, sub_lon_arr, units, sub_normals, output_file, month, TILE_LENGTH)

            if y % math.ceil(num_tiles/100) == 0:
                print('.', end='', flush=True)

        print()

def save_contours_png(lat_arr, lon_arr, units, normals, output_file, month, length=None):
    '''
    Saves contours in the data as a PNG file that is displayable over
    the map.
    '''
    # Latitude array is projected and will contain duplicates.
    # The Y axis must contain the projected number of distinct points or
    # contour function will just "unproject" the image.
    plot_lat_arr = np.linspace(lat_arr.size, 1, lat_arr.size)

    # Use dpi to ensure the plot takes up the expected dimensions in pixels.
    height = 1
    dpi = lon_arr.size if length is None else length
    #dpi = int(plot_lat_arr.size / height)
    width = height

    fig = plt.figure()
    fig.set_size_inches(width, height)
    ax = plt.Axes(fig, [0, 0, width, height])
    ax.set_axis_off()
    fig.add_axes(ax)

    contour_levels = get_contour_levels(units)
    contour_colours = get_contour_colours(contour_levels, units, month)

    cs = ax.contourf(lon_arr, plot_lat_arr, normals, levels=contour_levels, colors=contour_colours, extend='both')
    cs.cmap.set_over(contour_colours[-1])
    cs.cmap.set_under(contour_colours[0])
    cs.changed()
    plt.savefig(output_file, dpi=dpi, transparent=True)
    plt.close(fig)

def save_png(lat_arr, lon_arr, units, normals, output_file, month, length=None):
    '''
    Saves the data as a PNG image displayable over the map.
    '''
    if length is not None:
        # The resize does not honour the masked values, have to remask the array.
        normals = np.ma.masked_values(
            cv2.resize(normals, (length, length), interpolation=cv2.INTER_NEAREST),
            normals.fill_value
        )

    pixels = get_pixels(units, normals, month)
    png.from_array(pixels, 'RGB', info={
        'transparent': (0, 0, 0),
        'compression': 9,
    }).save(output_file)
