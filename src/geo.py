#!/usr/bin/env python3
#
# Geographic helper functions
#
# Copyright (c) 2020 Carlos Torchia
#
import numpy as np

EARTH_RADIUS = 6378137
EARTH_CIRCUMFERENCE = 2 * math.pi * EARTH_RADIUS

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
