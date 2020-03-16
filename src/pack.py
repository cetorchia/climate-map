#!/usr/bin/env python3
#
# This module is concerned with "packing" data into
# a format suitable for storage.
#
# Copyright (c) 2020 Carlos Torchia
#

import numpy as np

SCALE_FACTOR = 10
OUTPUT_DTYPE = np.int16
OUTPUT_DTYPE_MIN = np.iinfo(OUTPUT_DTYPE).min
OUTPUT_DTYPE_MAX = np.iinfo(OUTPUT_DTYPE).max

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
