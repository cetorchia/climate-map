#!/usr/bin/env python3
#
# API for serving climate tiles
#
# Copyright (c) 2020 Carlos Torchia
#

from flask import Flask
from flask import jsonify

import os

import tiling

app = Flask(__name__)

ALLOWED_MEASUREMENTS = ('tavg', 'precip')

ALLOWED_PERIODS = [
    '12_01_02',
    '03_04_05',
    '06_07_08',
    '09_10_11',
    'year',
]

@app.route('/climate/<string:data_source>/<int:start_year>-<int:end_year>/<string:measurement>-<string:period>/<int:zoom_level>/<int:x>/<int:y>.<string:ext>')
def climate_tile(data_source, start_year, end_year, measurement, period, zoom_level, x, y, ext):
    '''
    Serves the specified climate tile.
    '''
    if measurement not in ALLOWED_MEASUREMENTS:
        return jsonify({'error': 'Invalid measurement "%s"' % measurement}), 400

    if period not in ALLOWED_PERIODS:
        return jsonify({'error': 'Invalid period "%s"' % period}), 400

    if ext != tiling.TILE_EXTENSION:
        return jsonify({'error': 'Invalid extension "%s"' % ext}), 400

    try:
        tile_data = tiling.fetch_tile(data_source, start_year, end_year, measurement, period, zoom_level, x, y, ext)
        return tile_data, 200, {'Content-Type': 'image/' + ext}

    except tiling.TileNotFoundError:
        return jsonify({'error': 'Tile not found'}), 404

if __name__ == '__main__':
    app.run(processes=3, port=5001)
