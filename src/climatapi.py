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
        dataset = climatedb.fetch_dataset(data_source_id, start_date, end_date)

        dataset_id = dataset['id']
        delta = dataset['delta']
        error = math.sqrt(2*delta**2)

        data_point = climatedb.fetch_data_point_closest_to(dataset_id, lat, lon, error)

        normals = climatedb.fetch_monthly_normals_by_data_point(data_point['id'])

        normals.update({
            'lat': data_point['lat'],
            'lon': data_point['lon'],
        })

        return jsonify(normals)

    except climatedb.NotFoundError as e:
        return jsonify({'error': str(e)}), 404

@app.route('/data-sources')
def data_sources():
    '''
    Gives all active data sources.
    '''
    return jsonify(climatedb.fetch_data_sources())

@app.route('/datasets/<string:data_source>')
def datasets(data_source):
    '''
    Gives all datasets for the specified data source.
    '''
    try:
        data_source_id = climatedb.fetch_data_source(data_source)['id']
        return jsonify(climatedb.fetch_datasets(data_source_id))
    except climatedb.NotFoundError as e:
        return jsonify({'error': str(e)}), 404

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
