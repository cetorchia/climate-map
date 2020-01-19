#!/usr/bin/env python3
#
# API for serving climate data
#
# Copyright (c) 2020 Carlos Torchia
#

from datetime import date
from flask import Flask
from flask import jsonify
from werkzeug.routing import FloatConverter as BaseFloatConverter

import climatedb

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
        dataset_id = climatedb.fetch_dataset(data_source_id, start_date, end_date)['id']
        data_point = climatedb.fetch_data_point_closest_to(dataset_id, lat, lon)

        normals = climatedb.fetch_monthly_normals_by_data_point(data_point['id'])

        normals.update({
            'lat': data_point['lat'],
            'lon': data_point['lon'],
        })

        return jsonify(normals)

    except climatedb.NotFoundError as e:
        return jsonify({'error': str(e)}), 404
