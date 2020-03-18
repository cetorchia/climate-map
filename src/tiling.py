#!/usr/bin/env python3
#
# Functions for generating climate map tiles.
#
# Such tiles are used to show climate normals as colours on top
# of an actual map so that the user can visualize climate in their
# region.
#
# Copyright (c) 2020 Carlos Torchia
#
import os
import math
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as colors
import cv2

import climatedb
import arrays
import geo
import pack

TILE_LENGTH = 256
MAP_LENGTH = 16384
MAX_ZOOM_LEVEL = 7

def save_contour_tiles(y_arr, x_arr, units, normals, output_folder, data_source_id, tile=True):
    '''
    Generates map contour tiles for the specified climate normals
    in the specified output folder.

    The `tile` parameter specifies whether to generate tiles or save
    a large image that can later be tiled on-the-fly.
    '''
    full_output_file = output_folder + '.png'
    os.makedirs(os.path.dirname(full_output_file), exist_ok=True)
    save_contours(y_arr, x_arr, units, normals, full_output_file)

    if tile:
        img = cv2.imread(full_output_file)
        save_tiles(img, output_folder, data_source_id)

        os.remove(full_output_file)

def save_contours(y_arr, x_arr, units, normals, output_file, length=MAP_LENGTH, extent=None, contour=True):
    '''
    Saves contours in the data as a PNG file that is displayable over
    the map.
    '''
    extent = extent if extent else (
        -geo.EARTH_CIRCUMFERENCE/2,
        geo.EARTH_CIRCUMFERENCE/2,
        -geo.EARTH_CIRCUMFERENCE/2,
        geo.EARTH_CIRCUMFERENCE/2
    )

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

    if contour:
        cs = ax.contourf(x_arr, y_arr, normals, levels=contour_levels, colors=contour_colours, extend='both')
        cs.cmap.set_over(contour_colours[-1])
        cs.cmap.set_under(contour_colours[0])
        cs.changed()
    else:
        left_x, right_x = arrays.axis_limit_arrays(x_arr, (x_arr[1:] - x_arr[:-1]).mean())
        x_arr = np.append(left_x, right_x[-1])
        left_y, right_y = arrays.axis_limit_arrays(y_arr, lat2y(90) - y_arr[0])
        y_arr = np.append(left_y, right_y[-1])
        cmap = colors.ListedColormap(contour_colours)
        norm = colors.BoundaryNorm(contour_levels, len(contour_colours))
        ax.pcolormesh(x_arr, y_arr, normals, cmap=cmap, norm=norm)

    plt.savefig(output_file, dpi=dpi, transparent=True, quality=75)
    plt.close(fig)

def save_tiles(img, output_folder, data_source_id):
    '''
    Generates map tiles from the specified image in the specified folder.
    The max zoom level of the data source is updated so that the UI knows
    what zoom level to use, as this may have changed from other datasets.

    These tiles will use the same naming conventions/folder structure
    used by OpenStreetMap to not have to load the whole image. They will be stored
    as such in the specified output folder.

    E.g. /tiles/tavg-01/{z}/{x}/{y}.jpeg
    '''
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
    amount /= pack.SCALE_FACTOR

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
    amount /= pack.SCALE_FACTOR

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
