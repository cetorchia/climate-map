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

    if geoname['province']:
        try:
            province_geoname = geonamedb.fetch_geoname_by_province(geoname['province'], geoname['country'])

            try:
                geoname['province'] = geonamedb.fetch_abbreviation_by_geoname(province_geoname['geonameid'])
            except climatedb.NotFoundError:
                geoname['province'] = None

        except climatedb.NotFoundError:
            geoname['province'] = None

    if geoname['country']:
        try:
            country_geoname = geonamedb.fetch_geoname_by_country(geoname['country'])

            if country_geoname['geonameid'] == geoname['geonameid']:
                geoname['country'] = None

        except climatedb.NotFoundError:
            pass

    return jsonify(geoname)

@app.route('/places/<string:data_source>/<int:start_year>-<int:end_year>/<string:measurement>-<string:period>/<int:min_population>')
def climates_of_places(data_source, start_year, end_year, measurement, period, min_population):
    '''
    Gives the places with at least the specified  population, indexed by
    latitude and longitude, together with the specified measurement data.
    Only populous places or capitals are returned. Returning all possible
    places would be slow.

    Keys in the response take the form of integers i and j.
    For example:
    {
        "lat_start": 90,
        "lat_delta": -0.5,
        "lon_start": -180,
        "lon_delta": 0.5,
        1: {
            2: {
                "name": "Toronto",
                ...
                "tavg": {
                    0: [-4, "degC"],
                    1: [-4, "degC"],
                    ...
                },
                ...
            }
        }
    }

    In this case, you can use the "lat_start", "lat_delta", "lon_start", and
    "lon_delta" fields to figure out the index of any specific location. And
    thus you can use the array to look up the data for a populous place. If two
    places gets normalized to the same coordinates, the more populous one is used.
    '''
    start_date = date(start_year, 1, 1)
    end_date = date(end_year, 12, 31)
    measurement_id = climatedb.fetch_measurement(measurement)['id']

    if period != 'year':
        months = [int(month) - 1 for month in period.split('_')]
    else:
        months = range(0, 12)

    places = geonamedb.places_by_latitude_and_longitude(min_population)

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

                for i in places['geonames']:
                    for j in places['geonames'][i]:
                        geoname = places['geonames'][i][j]

                        lat = geoname['latitude']
                        lon = geoname['longitude']

                        try:
                            actual_lat, actual_lon, normals_arr = fetch_normals_by_location(dataset, lat, lon, False)
                            mean = normals_arr[months].mean()
                            geoname[measurement] = [mean, units]

                        except climatedb.NotFoundError:
                            # Presumably the place is in the ocean where there is no data.
                            pass

        return jsonify(places)

    except climatedb.NotFoundError as e:
        return jsonify({'error': str(e)}), 404

def fetch_normals_by_location(dataset, lat, lon, check_calibration=True):
    '''
    Gives climate normals calibrated against a baseline dataset for a specific latitude and longitude.
    If the dataset is not calibrated, we fetch the normals without calibrating.
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
