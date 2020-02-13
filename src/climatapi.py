#!/usr/bin/env python3
#
# API for serving climate data
#
# Copyright (c) 2020 Carlos Torchia
#

from datetime import date
import math
import json
import urllib
from flask import Flask
from flask import jsonify
from werkzeug.routing import FloatConverter as BaseFloatConverter

import climatedb
import climatetransform

NOMINATIM_API = 'https://nominatim.openstreetmap.org/search/'
NOMINATIM_DELAY = 1
USER_AGENT = 'Climate Map API'

app = Flask(__name__)

class FloatConverter(BaseFloatConverter):
    '''
    Float type in router doesn't support negative floats.
    Hack thanks to https://stackoverflow.com/a/20640550
    '''
    regex = r'-?\d+(\.\d+)?'

app.url_map.converters['float'] = FloatConverter

@app.before_request
def before():
    '''
    Connects to the database in preparation for the request.
    '''
    climatedb.connect('localhost:climate_map:climate_map')

@app.teardown_request
def teardown(error):
    '''
    Close the database when the request finishes.
    '''
    climatedb.close()

@app.route('/monthly-normals/<string:data_source>/<int:start_year>-<int:end_year>/<float:lat>/<float:lon>')
def monthly_normals(data_source, start_year, end_year, lat, lon):
    '''
    Gives the monthly normals for the specified latitude and longitude.
    '''
    start_date = date(start_year, 1, 1)
    end_date = date(end_year, 12, 31)

    try:
        data_source_id = climatedb.fetch_data_source(data_source)['id']
        datasets = climatedb.fetch_datasets(data_source_id, start_date, end_date)

        normals = {}

        for dataset in datasets:
            measurement = climatedb.fetch_measurement_by_id(dataset['measurement_id'])['code']
            units = climatedb.fetch_unit_by_id(dataset['unit_id'])['code']
            actual_lat, actual_lon, normals_arr = climatedb.fetch_monthly_normals(dataset, lat, lon)
            normals[measurement] = {(i + 1): [value.item(), units] for i, value in enumerate(normals_arr)}

        normals.update({
            'lat': actual_lat,
            'lon': actual_lon,
        })

        normals = climatetransform.unpack_normals(normals)

        return jsonify(normals)

    except climatedb.NotFoundError as e:
        return jsonify({'error': str(e)}), 404

@app.route('/date-ranges')
def date_ranges():
    '''
    Gives all available date ranges for which data exist.
    '''
    return jsonify(list(climatedb.fetch_date_ranges()))

@app.route('/data-sources/<int:start_year>-<int:end_year>')
def data_sources_by_date_range(start_year, end_year):
    '''
    Gives all data-sources for the specified date range and
    the corresponding dataset id for each one.
    '''
    start_date = date(start_year, 1, 1)
    end_date = date(end_year, 12, 31)
    datasets = climatedb.fetch_datasets_by_date_range(start_date, end_date)

    if datasets:
        data_source_ids = {dataset['data_source_id'] for dataset in datasets}
        data_sources = [
            climatedb.fetch_data_source_by_id(data_source_id)
            for data_source_id in data_source_ids
        ]

        return jsonify(data_sources)

    else:
        return jsonify({'error': 'Could not find date range %d-%d in the datasets' % (start_year, end_year)}), 404

@app.route('/search/<string:query>')
def search(query):
    '''
    Searches for the place specified in the query.
    '''
    climatedb.wait_search(NOMINATIM_DELAY)

    encoded_query = urllib.parse.quote(query)
    url = NOMINATIM_API + '/' + encoded_query + '?format=json&limit=1'
    request = urllib.request.Request(
        url,
        data=None,
        headers={
            'User-Agent': USER_AGENT,
        }
    )
    f = urllib.request.urlopen(request)

    if f.getcode() >= 400:
        return jsonify({'error': 'Error from Nominatim API'}), f.getcode()

    response = f.read()
    data = json.loads(response)

    if type(data) is list and len(data) == 1:
        new_data = data[0]
        new_data['lat'] = float(new_data['lat'])
        new_data['lon'] = float(new_data['lon'])

        return jsonify(new_data)
    else:
        return jsonify({'error': 'Unexpected result from Nominatim API'}), 500

if __name__ == '__main__':
    app.run(processes=3)
