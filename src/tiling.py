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
import config

TILE_ROOT = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tiles')

TILE_LENGTH = 256
ZOOM_LEVELS_PER_TILE = 2
META_TILE_LENGTH = TILE_LENGTH * 2 ** (ZOOM_LEVELS_PER_TILE - 1)
MAP_LENGTH = 16384
MAX_ZOOM_LEVEL = 7
TILE_EXTENSION = 'jpeg'
INITIAL_CONTOUR_EXTENSION = 'png'
FETCH_TILE_EXTENSION = 'png'
ALPHA_EXTENSION = 'png'
TILE_TRANSPARENT_VALUE = 255

MAP_EXTENT = (
    -geo.EARTH_CIRCUMFERENCE/2,
    geo.EARTH_CIRCUMFERENCE/2,
    -geo.EARTH_CIRCUMFERENCE/2,
    geo.EARTH_CIRCUMFERENCE/2
)

WATERMARK_IMAGE = os.path.join(os.path.dirname(os.path.dirname(__file__)), config.images.watermark.filename)
WATERMARK_OPACITY = config.images.watermark.opacity

if (MAX_ZOOM_LEVEL + 1) % ZOOM_LEVELS_PER_TILE != 0:
    raise Exception('The number of zoom levels, which is %d, must be divisible by the number of zoom levels per tile, which is %d.' % (MAX_ZOOM_LEVEL + 1, ZOOM_LEVELS_PER_TILE))

class TileNotFoundError(Exception):
    '''
    Thrown when the user requested a tile that does not exist.
    '''
    pass

def tile_folder(data_source, measurement, start_date, end_date, months=None):
    '''
    Gives the directory where tiles will be stored.

    Do not use this function to determine the path of a single tile;
    please use tile_path() for this instead.
    '''
    date_range = '%d-%d' % (start_date.year, end_date.year)

    if months:
        period = '%02d_%02d_%02d' % months
    else:
        period = 'year'

    tile_folder = os.path.join(TILE_ROOT, data_source, date_range, measurement + '-' + period)

    return tile_folder

def save_contour_tiles(y_arr, x_arr, units, normals, output_folder, data_source_id):
    '''
    Generates map contour tiles for the specified climate normals
    in the specified output folder.

    The `tile` parameter specifies whether to generate tiles or save
    a large image that can later be tiled on-the-fly.
    '''
    full_output_file = output_folder + '.' + INITIAL_CONTOUR_EXTENSION
    os.makedirs(os.path.dirname(full_output_file), exist_ok=True)
    save_contours(y_arr, x_arr, units, normals, full_output_file, MAP_LENGTH, MAP_EXTENT)

    img = cv2.imread(full_output_file, cv2.IMREAD_UNCHANGED)
    os.remove(full_output_file)
    save_tiles(img, output_folder, data_source_id)

def save_contours(y_arr, x_arr, units, normals, output_file, length, extent, contour=True):
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

    if contour:
        cs = ax.contourf(x_arr, y_arr, normals, levels=contour_levels, colors=contour_colours, extend='both')
        cs.cmap.set_over(contour_colours[-1])
        cs.cmap.set_under(contour_colours[0])
        cs.changed()
    else:
        left_x, right_x = arrays.axis_limit_arrays(x_arr, (x_arr[1:] - x_arr[:-1]).mean())
        x_arr = np.append(left_x, right_x[-1])
        left_y, right_y = arrays.axis_limit_arrays(y_arr, geo.lat2y(90) - y_arr[0])
        y_arr = np.append(left_y, right_y[-1])
        cmap = colors.ListedColormap(contour_colours)
        norm = colors.BoundaryNorm(contour_levels, len(contour_colours))
        ax.pcolormesh(x_arr, y_arr, normals, cmap=cmap, norm=norm)

    plt.savefig(output_file, dpi=dpi, transparent=True)
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

    tile_length = META_TILE_LENGTH
    ext = TILE_EXTENSION

    for zoom_level in range(0, max_zoom_level + 1):
        # Skip zoom levels already included in the previous zoom level
        if zoom_level % ZOOM_LEVELS_PER_TILE == 0:
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
                    resized_img = cv2.resize(img_xy, (tile_length, tile_length), fx=0.5, fy=0.5, interpolation=cv2.INTER_CUBIC)

                    output_parent = os.path.join(output_folder, str(zoom_level), str(x))
                    os.makedirs(output_parent, exist_ok=True)
                    output_file = os.path.join(output_parent, str(y) + '.' + ext)

                    cv2.imwrite(output_file, resized_img)

                    # Create alpha file to not lose transparency
                    if resized_img.shape[2] == 4 and ext in ('jpeg', 'jpg'):
                        alpha_file = os.path.join(output_parent, str(y) + '-alpha.' + ALPHA_EXTENSION)
                        alpha = resized_img[:, :, 3]
                        cv2.imwrite(alpha_file, alpha)

                if y % math.ceil(num_tiles/100) == 0:
                    print('.', end='', flush=True)

            print()

def get_contour_levels(units):
    '''
    Returns a list of the contour levels for use with pyplot.contourf()
    '''
    if units == 'degC':
        return np.hstack((np.arange(-100, -40, 10), np.arange(-40, 40, 5), np.arange(40, 101, 10))) * pack.SCALE_FACTOR

    elif units == 'mm':
        return np.hstack((np.arange(0, 100, 25), np.arange(100, 200, 50), np.arange(200, 1001, 100))) * pack.SCALE_FACTOR

    else:
        raise Exception('Unknown units: ' + units)

def get_contour_colours(levels, units):
    '''
    Returns a list of the contour colours for use with pyplot.contourf()
    '''
    levels = levels / pack.SCALE_FACTOR
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
    if amount >= 35:
        # 100: 50, 0, 0
        # 35: 255, 0, 0
        red = int(round(-205 / 65 * min(amount, 100) + 50 + 205 / 65 * 100))
        return red, 0, 0

    elif amount >= 0:
        # 35: 255, 0, 0
        # 0: 255, 238, 238
        green = blue = int(round(-238 / 35 * amount + 238))
        return 255, green, blue

    elif amount >= -35:
        # -5: 238, 238, 255
        # -35: 0, 0, 255
        red = green = int(round(238 / 30 * min(amount, -5) + 35 * 238 / 30))
        return red, green, 255

    else:
        # -35: 0, 0, 255
        # -100: 0, 0, 50
        blue = int(round(205 / 65 * min(amount, 100) + 50 + 205 / 65 * 100))
        return 0, 0, blue

def precipitation_millimetres_colour(amount):
    '''
    Returns the colour for the specified mm of precipitation.
    '''
    if amount >= 500:
        # 1000: 0, 0, 50
        # 500: 0, 0, 255
        blue = int(round(-41 / 100 * min(amount, 1000) + 460))
        return 0, 0, blue

    elif amount >= 400:
        return 50, 50, 255
    elif amount >= 300:
        return 100, 100, 255
    elif amount >= 200:
        return 0, 255, 0
    elif amount >= 150:
        return 50, 255, 50
    elif amount >= 100:
        return 100, 255, 100
    elif amount >= 75:
        return 150, 255, 150
    elif amount >= 50:
        return 200, 255, 200
    elif amount >= 25:
        return 230, 230, 180
    else:
        return 245, 220, 100

def fetch_tile(data_source, start_year, end_year, measurement, period, zoom_level, x, y, ext):
    '''
    Fetches the specified tile.
    If more than one zoom level per tile is used, the metatile will be divided
    to extract the sub-tile.
    '''
    sub_zoom_level = zoom_level % ZOOM_LEVELS_PER_TILE
    meta_zoom_level = zoom_level - sub_zoom_level
    division = 2 ** sub_zoom_level

    meta_x = x // division
    meta_y = y // division

    stored_ext = TILE_EXTENSION
    path = tile_path(data_source, start_year, end_year, measurement, period, meta_zoom_level, meta_x, meta_y, stored_ext)
    alpha_path = tile_alpha_path(data_source, start_year, end_year, measurement, period, meta_zoom_level, meta_x, meta_y)

    tile_img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    alpha_img = cv2.imread(alpha_path, cv2.IMREAD_UNCHANGED)

    sub_x = x % division
    sub_y = y % division

    sub_tile_length = int(META_TILE_LENGTH / division)
    start_x = sub_x * sub_tile_length
    end_x = start_x + sub_tile_length

    start_y = sub_y * sub_tile_length
    end_y = start_y + sub_tile_length

    subtile_img = tile_img[start_y:end_y, start_x:end_x]
    subalpha_img = alpha_img[start_y:end_y, start_x:end_x]

    if subtile_img.shape != (TILE_LENGTH, TILE_LENGTH):
        subtile_img = cv2.resize(subtile_img, (TILE_LENGTH, TILE_LENGTH), fx=0.5, fy=0.5, interpolation=cv2.INTER_NEAREST)

    if subalpha_img.shape != (TILE_LENGTH, TILE_LENGTH):
        subalpha_img = cv2.resize(subalpha_img, (TILE_LENGTH, TILE_LENGTH), fx=0.5, fy=0.5, interpolation=cv2.INTER_NEAREST)

    subtile_img = add_transparency(subtile_img, subalpha_img)
    subtile_img = add_watermark(subtile_img)

    success, subtile_data = cv2.imencode('.' + ext, subtile_img)

    if success:
        return subtile_data.tostring()
    else:
        raise Exception('Error encoding tile image to %s' % ext)

def tile_path(data_source, start_year, end_year, measurement, period, zoom_level, x, y, ext):
    '''
    Gives the path of the specified tile.
    Throws TileNotFoundError if not found.
    '''
    date_range = '%d-%d' % (start_year, end_year)
    measurement_period = '%s-%s' % (measurement, period)
    y_ext = '%d.%s' % (y, ext)
    path = build_path(TILE_ROOT, data_source, date_range, measurement_period, zoom_level, x, y_ext)

    if not path:
        raise TileNotFoundError()

    return path

def tile_alpha_path(data_source, start_year, end_year, measurement, period, zoom_level, x, y):
    '''
    Gives the path of the specified tile's alpha channel.
    Throws TileNotFoundError if not found.
    '''
    date_range = '%d-%d' % (start_year, end_year)
    measurement_period = '%s-%s' % (measurement, period)
    y_ext = '%d-alpha.%s' % (y, ALPHA_EXTENSION)
    path = build_path(TILE_ROOT, data_source, date_range, measurement_period, zoom_level, x, y_ext)

    if not path:
        raise TileNotFoundError()

    return path

def build_path(*parts):
    '''
    Builds a path from the specified parts that is immune to '..' attacks.
    Returns parts[0] + '/' + parts[1] + '/' + ... + '/' + parts[n] assuming os.sep is '/'
    Returns None if the path does not exist, including if '..' or '.' are elements in the path.
    '''
    path = str(parts[0])

    for part in parts[1:]:
        part = str(part)
        if part.find('/') != -1:
            return None
        elif part.find(os.sep) != -1:
            return None
        elif path.find('..') != -1:
            return None
        elif part not in os.listdir(path):
            return None
        else:
            path = path + os.sep + part

    if path.find('..') != -1:
        return None

    return path

def add_transparency(img, alpha):
    '''
    Adds transparency to a tile that does not have it.
    This is especially the case when we save tiles in JPEG to save space.
    The alpha parameter is a numpy array with the alpha channel.
    '''
    return np.append(img, alpha.reshape(img.shape[:2] + (1,)), axis=2)

def add_watermark(img):
    '''
    Adds the copyright watermark to the specified image.
    If the image is bigger than the watermark image, then we
    repeat the image horizontally and vertically in an effort
    to show the copyright on every sub-tile.

    The watermark image must be exactly the same size as each
    tile. See TILE_LENGTH.
    '''
    if WATERMARK_IMAGE and os.path.exists(WATERMARK_IMAGE):
        watermark_img = cv2.imread(WATERMARK_IMAGE, cv2.IMREAD_UNCHANGED)

        if watermark_img.shape[:2] != img.shape[:2]:
            raise Exception('Expected watermark image to fit evenly on each tile. Check size of %s is 256x256' % WATERMARK_IMAGE)

        if watermark_img.shape[2] != img.shape[2]:
            raise Exception('Expected watermark image to have the same depth as each tile. Check alpha layer')

        final_img = img.copy()
        final_img = cv2.addWeighted(watermark_img, WATERMARK_OPACITY, final_img, 1.0, 0, final_img)

        return final_img
    else:
        return img
