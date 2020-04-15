#!/usr/bin/env python3
#
# This module is concerned with "packing" data into
# a format suitable for storage.
#
# Copyright (c) 2020 Carlos Torchia
#

import sys
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

    missing_value = data_arr.fill_value

    if (missing_value < OUTPUT_DTYPE_MIN or missing_value > OUTPUT_DTYPE_MAX):
        new_missing_value = OUTPUT_DTYPE_MIN

        if np.any(data_arr.data == new_missing_value):
            raise Exception('Data cannot contain %d as this is needed for missing values' % new_missing_value)

        if np.any(data_arr.mask):
            np.place(data_arr.data, data_arr.mask, new_missing_value)

        data_arr.set_fill_value(new_missing_value)

        if np.any(data_arr.mask != (data_arr.data == new_missing_value)):
            raise Exception('Expected mask to all and only contain new missing value')

    mask_out_of_bounds(data_arr)

    return np.round(data_arr).astype(OUTPUT_DTYPE)

def mask_out_of_bounds(data_arr):
    '''
    Masks any values out of bounds for the OUTPUT_DTYPE
    '''
    out_of_bounds = (data_arr < OUTPUT_DTYPE_MIN) | (data_arr > OUTPUT_DTYPE_MAX)

    if np.any(out_of_bounds):
        num_out_of_bounds = len(np.where(out_of_bounds)[0])
        print('Warning: Data contains %d values out of range (%d..%d) for a %s. Masking.' % (
                 num_out_of_bounds, OUTPUT_DTYPE_MIN, OUTPUT_DTYPE_MAX, OUTPUT_DTYPE
              ),
              file=sys.stderr)

        data_arr[out_of_bounds] = np.ma.masked
        np.place(data_arr.data, out_of_bounds, data_arr.fill_value)
