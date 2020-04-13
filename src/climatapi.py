#!/usr/bin/env python3
#
# API for serving climate data
#
# Copyright (c) 2020 Carlos Torchia
#

from datetime import date
import numpy as np
from flask import Flask
from flask import jsonify
from flask import request
from werkzeug.routing import FloatConverter as BaseFloatConverter

import climatedb
import geonamedb
import pack
import calibration

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
    climatedb.connect()

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
        data_source_record = climatedb.fetch_data_source(data_source)
        data_source_id = data_source_record['id']

        if data_source_record['baseline']:
            calibrated = False
        else:
            calibrated = True

        datasets = climatedb.fetch_datasets(data_source_id, start_date, end_date, calibrated)

        normals = {}

        for dataset in datasets:
            measurement = climatedb.fetch_measurement_by_id(dataset['measurement_id'])['code']
            units = climatedb.fetch_unit_by_id(dataset['unit_id'])['code']

            actual_lat, actual_lon, normals_arr = fetch_normals_by_location(dataset, lat, lon)

            normals[measurement] = {(m + 1): [value.item(), units] for m, value in enumerate(normals_arr)}

        normals.update({
            'lat': actual_lat,
            'lon': actual_lon,
        })

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
        data_source_ids = {(dataset['data_source_id'], dataset['calibrated']) for dataset in datasets}
        data_sources = [
            (climatedb.fetch_data_source_by_id(data_source_id), calibrated)
            for data_source_id, calibrated in data_source_ids
        ]
        selected_data_sources = [
            data_source_record
            for data_source_record, calibrated in data_sources
            if calibrated or data_source_record['baseline']
        ]
        selected_data_sources.sort(key=lambda data_source_record: data_source_record['name'])

        return jsonify(selected_data_sources)

    else:
        return jsonify({'error': 'Could not find date range %d-%d in the datasets' % (start_year, end_year)}), 404

@app.route('/search/<string:query>')
def search(query):
    '''
    Searches for the place specified in the query.
    '''
    try:
        geoname = geonamedb.search_geoname(query)
    except climatedb.NotFoundError:
        return jsonify({'error': 'Search found no results for "%s"' % query}), 404

    geoname['province'] = geonamedb.get_human_readable_province(geoname)
    geoname['country'] = geonamedb.get_human_readable_country(geoname)

    return jsonify(geoname)

@app.route('/places/<string:data_source>/<int:start_year>-<int:end_year>/<string:measurement>-<string:period>')
def climates_of_places(data_source, start_year, end_year, measurement, period):
    '''
    Gives the list of the most populated places within the specified
    bounding box, together with the specified measurements.

    The bounding box must be specified in the min_lat, max_lat, min_lon, and max_lon
    the GET parameters.
    '''
    try:
        min_lat = float(request.args.get('min_lat'))
        max_lat = float(request.args.get('max_lat'))
        min_lon = float(request.args.get('min_lon'))
        max_lon = float(request.args.get('max_lon'))

    except TypeError:
        return jsonify({'error': 'Invalid coordinates'}), 400

    start_date = date(start_year, 1, 1)
    end_date = date(end_year, 12, 31)
    measurement_id = climatedb.fetch_measurement(measurement)['id']

    if period != 'year':
        months = [int(month) - 1 for month in period.split('_')]
    else:
        months = range(0, 12)

    geonames = list(geonamedb.fetch_populous_places_within_area(min_lat, max_lat, min_lon, max_lon))

    for geoname in geonames:
        geoname['province'] = geonamedb.get_human_readable_province(geoname)
        geoname['country'] = geonamedb.get_human_readable_country(geoname)

    try:
        data_source_record = climatedb.fetch_data_source(data_source)
        data_source_id = data_source_record['id']

        if data_source_record['baseline']:
            calibrated = False
        else:
            calibrated = True

        datasets = climatedb.fetch_datasets(data_source_id, start_date, end_date, calibrated)

        for dataset in datasets:
            if measurement_id == dataset['measurement_id']:
                units = climatedb.fetch_unit_by_id(dataset['unit_id'])['code']

                for geoname in geonames:
                    lat = geoname['latitude']
                    lon = geoname['longitude']

                    try:
                        actual_lat, actual_lon, normals_arr = fetch_normals_by_location(dataset, lat, lon, False)
                        mean = normals_arr[months].mean()
                        geoname[measurement] = [mean, units]

                    except climatedb.NotFoundError:
                        # Presumably the place is in the ocean where there is no data.
                        pass

        return jsonify(geonames)

    except climatedb.NotFoundError as e:
        return jsonify({'error': str(e)}), 404

def fetch_normals_by_location(dataset, lat, lon, check_calibration=True):
    '''
    Gives climate normals calibrated against a baseline dataset for a
    specific latitude and longitude.  If the dataset is not calibrated,
    we fetch the normals without calibrating.
    '''
    calibrated = dataset['calibrated']

    if calibrated:
        calibrated_lat, calibrated_lon, calibrated_normals_arr = calibration.calibrate_location(
            dataset,
            lat,
            lon
        )

    try:
        actual_lat, actual_lon, normals_arr = climatedb.fetch_monthly_normals(dataset, lat, lon)

    except FileNotFoundError as e:
        if calibrated:
            return calibrated_lat, calibrated_lon, calibrated_normals_arr / pack.SCALE_FACTOR
        else:
            raise e

    if calibrated:
        if (actual_lat, actual_lon) != (calibrated_lat, calibrated_lon):
            raise Exception('Expected calibrated coordinates to match those from on-the-fly calibration')

        if check_calibration and np.any(normals_arr != calibrated_normals_arr):
            raise Exception('Expected calibrated normals to correspond with on-the-fly calibration')

        return calibrated_lat, calibrated_lon, calibrated_normals_arr / pack.SCALE_FACTOR

    else:
        return actual_lat, actual_lon, normals_arr / pack.SCALE_FACTOR

if __name__ == '__main__':
    app.run(processes=3)
