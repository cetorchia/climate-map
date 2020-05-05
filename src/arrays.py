#!/usr/bin/env python3
#
# Functions for working with arrays, especially
# for downscaling.
#
# Copyright (c) 2020 Carlos Torchia
#

import numpy as np

import pack

def assert_fill_value(data_arr):
    '''
    Asserts that the specified array is masked and that
    the fill value is in exactly the masked elements.
    '''
    if not isinstance(data_arr, np.ma.masked_array) \
    or np.any(data_arr.fill_value != data_arr[data_arr.mask]) \
    or np.any(data_arr.fill_value == data_arr[~data_arr.mask]):
        raise Exception('Expected masked array with fill value in and only in the masked portion')

def is_increasing(arr):
    # See https://stackoverflow.com/a/4983359
    return all(x<y for x, y in zip(arr, arr[1:]))

def is_decreasing(arr):
    # See https://stackoverflow.com/a/4983359
    return all(x>y for x, y in zip(arr, arr[1:]))

def start_delta(arr):
    '''
    Returns the start value and delta value for the specific latitude or
    longitude array.

    For example, if the coordinate array is [-180, -179.5, 179, ..., 179.5],
    then this function would return (-180, 0.5).
    '''
    start = arr[0].item()
    delta = (arr[arr.size - 1] - arr[0]) / (arr.size - 1)

    return start, delta

def find_lat_index(lat_arr, lat_delta, lat):
    '''
    Finds the index of the specified latitude in the latitude array.
    '''
    return find_coordinate_index(lat_arr, lat_delta, lat)

def find_lon_index(lon_arr, lon_delta, lon):
    '''
    Finds the index of the specified longitude in the longitude array.
    '''
    # If the longitude is beyond the last data point, e.g. 179.9, we resolve it
    # to -180.
    if lon_delta > 0:
        if lon >= lon_arr[-1] + lon_delta / 2:
            lon -= 360
    else:
        raise Exception('Unsupported: decreasing longitudes in dataset')

    return find_coordinate_index(lon_arr, lon_delta, lon)

def find_coordinate_index(coord_arr, coord_delta, coord):
    '''
    Finds the index of the coordinate in the coordinate array.
    Note that the coordinate may not actually be a value in the array,
    but we will return the index whose value is closest to the specified
    coordinate.
    '''
    left_axis_limit = coord_arr[0] - coord_delta
    right_axis_limit = coord_arr[-1] + coord_delta

    coord_arr = np.append(np.append(left_axis_limit, coord_arr), right_axis_limit)

    if coord_delta > 0:
        i = np.where(((coord_arr[:-2] + coord_arr[1:-1]) / 2 <= coord) & (coord < (coord_arr[1:-1] + coord_arr[2:]) / 2))[0]
    else:
        i = np.where(((coord_arr[:-2] + coord_arr[1:-1]) / 2 > coord) & (coord >= (coord_arr[1:-1] + coord_arr[2:]) / 2))[0]

    if len(i) == 0:
        raise Exception('Coordinate %g is out the range' % coord)

    return i[0]

def axis_limit_arrays(axis_arr, axis_delta):
    '''
    Returns left and right axis limit arrays. Each element provides
    the limit that points in the range of the coordinate must greater than or
    equal to and less than respectively.
    '''
    # Note: if axis array is decreasing (as in the case of latitudes),
    # left axis limit is still the lower limit of these coordinates, so we
    # still need to subtract (and not add) the delta / 2.
    # Similarly, we still need to add the delta / 2 to the right axis limit
    # as this number will be greater than all coordinate elements.
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

    right_idx = baseline_axis_arr.size - mask_right

    downscaled_axis_arr = np.ma.zeros(baseline_axis_arr.size)
    downscaled_axis_arr.mask = np.repeat(False, downscaled_axis_arr.size)
    downscaled_axis_arr.mask[:mask_left] = True
    downscaled_axis_arr.mask[right_idx:] = True
    downscaled_axis_arr[mask_left:right_idx] = np.repeat(axis_arr, axis_repeats)

    num_downscaled = np.nonzero(~downscaled_axis_arr.mask)[0].size

    if num_downscaled != axis_repeats.sum():
        raise Exception('Expected number %d of non-masked downscaled axis elements to be %d' % (
            num_downscaled, axis_repeats.sum()))

    return mask_left, mask_right, downscaled_axis_arr, axis_repeats

def _check_downscaled_axis_arr(
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

    _check_downscaled_axis_arr(baseline_lat_arr, downscaled_lat_arr,
                              left_lat_limit_arr, right_lat_limit_arr, lat_repeats)
    _check_downscaled_axis_arr(baseline_lon_arr, downscaled_lon_arr,
                              left_lon_limit_arr, right_lon_limit_arr, lon_repeats)

    downscaled_data_arr = np.ma.empty((downscaled_lat_arr.size, downscaled_lon_arr.size))
    downscaled_data_arr.mask = np.repeat(False, downscaled_data_arr.size).reshape(downscaled_data_arr.shape)
    downscaled_data_arr.set_fill_value(
        data_arr.fill_value if isinstance(data_arr, np.ma.masked_array) else pack.OUTPUT_DTYPE_MIN
    )

    downscaled_data_arr.mask[downscaled_lat_arr.mask, :] = True
    downscaled_data_arr.data[downscaled_lat_arr.mask, :] = downscaled_data_arr.fill_value
    downscaled_data_arr.mask[:, downscaled_lon_arr.mask] = True
    downscaled_data_arr.data[:, downscaled_lon_arr.mask] = downscaled_data_arr.fill_value

    downscaled_data_subarr = np.repeat(data_arr, lat_repeats, axis=0)
    downscaled_data_subarr = np.repeat(downscaled_data_subarr, lon_repeats, axis=1)

    lat_right_idx = downscaled_lat_arr.size - lat_mask_right
    lon_right_idx = downscaled_lon_arr.size - lon_mask_right
    downscaled_data_arr[lat_mask_left:lat_right_idx, lon_mask_left:lon_right_idx] = downscaled_data_subarr

    fix_missing_longitudes(baseline_lon_arr, lon_arr, lon_delta, downscaled_data_arr, lon_mask_left,
                           lon_mask_left + lon_mask_right)

    return downscaled_data_arr

def fix_missing_longitudes(baseline_lon_arr, lon_arr, lon_delta, downscaled_data_arr, lon_mask_left, total_lon_masked):
    '''
    Adds data for missing longitudes to calibrated data at the edge of the map
    because the point that they fall within is on the other side (the earth is round).

    Data for these longitudes will be added to the already-downscaled data array
    that you pass in.

    For simplicity, for now, since all of the datasets so far start at -180, we
    will only add missing longitudes at the east end of the globe. If there are
    missing longitudes on the west, we throw an exception.
    '''
    if not is_increasing(baseline_lon_arr):
        raise Exception('Expected baseline longitude array to be increasing')

    if not is_increasing(lon_arr):
        raise Exception('Expected forecast longitude array to be increasing')

    lon_min = lon_arr[0]
    lon_max = lon_arr[-1]

    if np.any(baseline_lon_arr < lon_min - lon_delta / 2) or np.all(downscaled_data_arr.mask[:, 0]) or lon_mask_left != 0:
        raise Exception('Unsupported: missing longitudes on the west side of globe that need to be copied '
                        'from the east side (the earth is round). Try making longitudes start at -180 and '
                        'this should work, or change this function to copy data from longitude 180.')

    lon_arr_within_min = (
        (baseline_lon_arr >= lon_max + lon_delta / 2) &
        (baseline_lon_arr - 360 >= lon_min - lon_delta / 2) &
        (baseline_lon_arr - 360 < lon_min)
    )

    if len(np.where(lon_arr_within_min)[0]) != total_lon_masked:
        raise Exception('Expected baseline longitudes that are within the minimum forecast longitude to be'
                        'as many as those that were masked during the downscaling process.')

    data_from_lon_min = downscaled_data_arr[:, lon_mask_left].reshape((downscaled_data_arr.shape[0], 1))
    downscaled_data_arr[:, lon_arr_within_min] = data_from_lon_min
