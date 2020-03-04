#!/usr/bin/env python3
#
# Climate database
#
# Copyright (c) 2020 Carlos Torchia
#

import MySQLdb
import re
import math
from datetime import datetime
import time
import os.path
import numpy as np

import config

# Global database object
db = None

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')

DATA_DTYPE = np.int16
LAT_DTYPE = LON_DTYPE = np.float64

MONTHS_PER_YEAR = 12

CHARSET = 'utf8mb4'

def connect():
    '''
    Connects to the specified db
    '''
    global db

    if db is not None:
        db.conn.close()

    db = Db(
        name=config.database.name,
        host=config.database.host,
        user=config.database.user,
        password=config.database.password
    )

def rollback():
    '''
    Rolls the transaction back.
    '''
    db.conn.rollback()

def commit():
    '''
    Commits the transaction.
    '''
    db.conn.commit()

def close():
    '''
    Closes the database
    '''
    db.cur.close()
    db.conn.close()

class Db:
    '''
    Represents a database
    '''
    def __init__(self, host, name, user, password=None, port=None, charset=CHARSET):

        if port is None:
            self.conn = MySQLdb.connect(host=host, db=name, passwd=password, user=user, charset=charset)
        else:
            self.conn = MySQLdb.connect(host=host, port=port, db=name, user=user, passwd=password, charset=charset)

        self.cur = self.conn.cursor()

class NotFoundError(Exception):
    '''
    Thrown when a record is not found.
    '''
    pass

def fetch_unit_by_id(unit_id):
    '''
    Fetches the specified unit by ID
    '''
    db.cur.execute('SELECT code, name FROM units WHERE id = %s', (unit_id,))
    row = db.cur.fetchone()

    if row is None:
        raise NotFoundError('Could not find unit %d' % unit_id)

    units, unit_name = row

    return {
        'id': unit_id,
        'code': units,
        'name': unit_name,
    }

def fetch_unit(units):
    '''
    Fetches the specified unit record using the specified units code (e.g. 'degC', 'mm').
    '''
    db.cur.execute('SELECT id, name FROM units WHERE code = %s', (units,))
    row = db.cur.fetchone()

    if row is None:
        raise NotFoundError('Could not find units "%s"' % units)

    unit_id, unit_name = row

    return {
        'id': unit_id,
        'code': units,
        'name': unit_name,
    }

def fetch_measurement_by_id(measurement_id):
    '''
    Fetches the specified measurement
    '''
    db.cur.execute('SELECT code, name FROM measurements WHERE id = %s', (measurement_id,))
    row = db.cur.fetchone()

    if row is None:
        raise NotFoundError('Could not find measurement %d' % measurement_id)

    measurement, measurement_name = row

    return {
        'id': measurement_id,
        'code': measurement,
        'name': measurement_name,
    }

def fetch_measurement(measurement):
    '''
    Fetches the specified measurement
    '''
    db.cur.execute('SELECT id, name FROM measurements WHERE code = %s', (measurement,))
    row = db.cur.fetchone()

    if row is None:
        raise NotFoundError('Could not find measurement "%s"' % measurement)

    measurement_id, measurement_name = row

    return {
        'id': measurement_id,
        'code': measurement,
        'name': measurement_name,
    }

def fetch_data_source_by_id(data_source_id):
    '''
    Fetches the specified data source
    '''
    db.cur.execute(
        '''
        SELECT id, code, name, organisation, url, author, year, max_zoom_level, baseline, active
        FROM data_sources
        WHERE id = %s
        ''',
        (data_source_id,)
    )
    row = db.cur.fetchone()

    if row is None:
        raise NotFoundError('Could not find data source %d' % data_source_id)

    data_source_id, code, name, organisation, url, author, year, max_zoom_level, baseline, active = row

    return {
        'id': data_source_id,
        'code': code,
        'name': name,
        'organisation': organisation,
        'url': url,
        'author': author,
        'year': year,
        'max_zoom_level': max_zoom_level,
        'baseline': baseline,
        'active': active,
    }

def fetch_data_source(data_source_code):
    '''
    Fetches the specified data source
    '''
    db.cur.execute(
        '''
        SELECT id, name, organisation, url, author, year, max_zoom_level, baseline, active
        FROM data_sources
        WHERE code = %s
        ''',
        (data_source_code,)
    )
    row = db.cur.fetchone()

    if row is None:
        raise NotFoundError('Could not find data source "%s"' % data_source_code)

    data_source_id, name, organisation, url, author, year, max_zoom_level, baseline, active = row

    return {
        'id': data_source_id,
        'code': data_source_code,
        'name': name,
        'organisation': organisation,
        'url': url,
        'author': author,
        'year': year,
        'max_zoom_level': max_zoom_level,
        'baseline': baseline,
        'active': active,
    }

def update_max_zoom_level(data_source_id, max_zoom_level):
    '''
    Updates the max zoom level of the specified data source
    '''
    db.cur.execute(
        '''
        UPDATE data_sources
        SET max_zoom_level = GREATEST(%s, max_zoom_level)
        WHERE id = %s
        ''',
        (max_zoom_level, data_source_id)
    )

def fetch_date_ranges():
    '''
    Fetches all date ranges for available datasets in the system.
    '''
    db.cur.execute(
        '''
        SELECT year(start_date) AS start_year, year(end_date) AS end_year
        FROM datasets d
        INNER JOIN data_sources s ON s.id = d.data_source_id
        WHERE s.active
        GROUP BY 1, 2
        ORDER BY 1, 2
        '''
    )

    rows = db.cur.fetchall()

    return ('%d-%d' % (start_year, end_year) for start_year, end_year in rows)

def fetch_datasets_by_date_range(start_date, end_date):
    '''
    Fetches the datasets matching the specified date range.
    '''
    db.cur.execute(
        '''
        SELECT id, data_source_id, calibrated FROM datasets
        WHERE start_date = %s AND end_date = %s
        ''',
        (start_date, end_date)
    )
    rows = db.cur.fetchall()

    return (
        {
            'id': dataset_id,
            'data_source_id': data_source_id,
            'calibrated': calibrated,
        }
        for dataset_id, data_source_id, calibrated in rows
    )

def fetch_dataset(data_source_id, measurement_id, unit_id, start_date, end_date, calibrated):
    '''
    Fetches the specified dataset.
    '''
    db.cur.execute(
        '''
        SELECT
            id,
            lat_start,
            lat_delta,
            lon_start,
            lon_delta,
            fill_value,
            data_filename,
            lat_filename,
            lon_filename
        FROM datasets
        WHERE data_source_id = %s
        AND measurement_id = %s AND unit_id = %s
        AND start_date = %s AND end_date = %s
        AND calibrated = %s
        ''',
        (data_source_id, measurement_id, unit_id, start_date, end_date, calibrated)
    )
    row = db.cur.fetchone()

    if row is None:
        raise NotFoundError(
            'Could not find dataset for data source %d, measurement %d, unit %d, start_date %s, and end_date %s' % (
                data_source_id, measurement_id, unit_id, start_date, end_date
            ))

    (
        dataset_id,
        lat_start,
        lat_delta,
        lon_start,
        lon_delta,
        fill_value,
        data_filename,
        lat_filename,
        lon_filename,
    ) = row

    return {
        'id': dataset_id,
        'lat_start': lat_start,
        'lat_delta': lat_delta,
        'lon_start': lon_start,
        'lon_delta': lon_delta,
        'fill_value': fill_value,
        'data_filename': data_filename,
        'lat_filename': lat_filename,
        'lon_filename': lon_filename,
    }

def fetch_datasets(data_source_id, start_date, end_date, calibrated):
    '''
    Fetches the datasets with the specified data source, start date, and end date.
    '''
    db.cur.execute(
        '''
        SELECT
            id,
            measurement_id,
            unit_id,
            lat_start,
            lat_delta,
            lon_start,
            lon_delta,
            fill_value,
            data_filename,
            lat_filename,
            lon_filename,
            calibrated
        FROM datasets
        WHERE data_source_id = %s
        AND start_date = %s AND end_date = %s
        AND calibrated = %s
        ''',
        (data_source_id, start_date, end_date, calibrated)
    )
    rows = db.cur.fetchall()

    if rows is None:
        raise NotFoundError('Could not find datasets for data source %d, start_date %s, and end_date %s' % (
            data_source_id, start_date, end_date
        ))

    return (
        {
            'id': dataset_id,
            'measurement_id': measurement_id,
            'unit_id': unit_id,
            'lat_start': lat_start,
            'lat_delta': lat_delta,
            'lon_start': lon_start,
            'lon_delta': lon_delta,
            'fill_value': fill_value,
            'data_filename': data_filename,
            'lat_filename': lat_filename,
            'lon_filename': lon_filename,
            'calibrated': calibrated,
        }
        for (
            dataset_id,
            measurement_id,
            unit_id,
            lat_start,
            lat_delta,
            lon_start,
            lon_delta,
            fill_value,
            data_filename,
            lat_filename,
            lon_filename,
            calibrated,
        )
        in rows
    )

def create_dataset(
        data_source_id,
        measurement_id,
        unit_id,
        start_date,
        end_date,
        lat_start,
        lat_delta,
        lon_start,
        lon_delta,
        fill_value,
        data_filename,
        lat_filename,
        lon_filename,
        calibrated
):
    '''
    Creates a new dataset for the specified data source, start date, and end date.
    '''
    db.cur.execute(
        '''
        INSERT INTO datasets(
            data_source_id,
            measurement_id,
            unit_id,
            start_date,
            end_date,
            lat_start,
            lat_delta,
            lon_start,
            lon_delta,
            fill_value,
            data_filename,
            lat_filename,
            lon_filename,
            calibrated
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''',
        (
            data_source_id,
            measurement_id,
            unit_id,
            start_date,
            end_date,
            lat_start,
            lat_delta,
            lon_start,
            lon_delta,
            fill_value,
            data_filename,
            lat_filename,
            lon_filename,
            calibrated
        )
    )

    return fetch_dataset(data_source_id, measurement_id, unit_id, start_date, end_date, calibrated)

def create_monthly_normals(
        data_source,
        start_year,
        end_year,
        measurement,
        units,
        lat_arr,
        lon_arr,
        data_arr,
        month,
        calibrated
):
    '''
    Saves the specified monthly normal values.
    This can be either a 2-D array for a specific month or a 3-D array
    containing all months as axis 0.
    '''
    if month < 1 or month > MONTHS_PER_YEAR:
        raise Exception('Expected month to be 1 to 12, got %d' % month)

    if data_arr.ndim != 2:
        raise Exception('Expected 2-D array')

    if data_arr.dtype != DATA_DTYPE:
        raise Exception('Expected datatype to be %s, got %s' % (DATA_DTYPE, data_arr.dtype))

    if lat_arr.dtype != LAT_DTYPE:
        raise Exception('Expected latitude datatype to be %s, got %s' % (LAT_DTYPE, lat_arr.dtype))

    if lon_arr.dtype != LON_DTYPE:
        raise Exception('Expected longitude datatype to be %s, got %s' % (LON_DTYPE, lon_arr.dtype))

    if not isinstance(data_arr, np.ma.masked_array) \
    or np.any(data_arr.fill_value != data_arr[data_arr.mask]) \
    or np.any(data_arr.fill_value == data_arr[~data_arr.mask]):
        raise Exception('Expected masked array with fill value in and only in the masked portion')

    base_name = '%s-%d-%d-%s-%s' % (data_source, start_year, end_year, measurement, units)
    if calibrated:
        base_name += '-calibrated'

    data_basename = base_name + '-data.mmap'
    lat_basename = base_name + '-lat.mmap'
    lon_basename = base_name + '-lon.mmap'

    data_pathname = os.path.join(DATA_DIR, data_basename)
    lat_pathname = os.path.join(DATA_DIR, lat_basename)
    lon_pathname = os.path.join(DATA_DIR, lon_basename)

    if os.path.exists(data_pathname):
        data_mmap = np.memmap(data_pathname, dtype=data_arr.dtype, mode='r+', shape=(MONTHS_PER_YEAR,) + data_arr.shape)
    else:
        # Bug? 'w+' replaces all contents of the array with 0
        data_mmap = np.memmap(data_pathname, dtype=data_arr.dtype, mode='w+', shape=(MONTHS_PER_YEAR,) + data_arr.shape)

    data_mmap[month - 1, :] = data_arr

    del data_mmap

    if os.path.exists(lat_pathname):
        lat_mmap = np.memmap(lat_pathname, dtype=lat_arr.dtype, mode='r')
        if np.any(lat_mmap[:] != lat_arr):
            raise Exception('Expected latitude array to be the same')
    else:
        lat_mmap = np.memmap(lat_pathname, dtype=lat_arr.dtype, mode='w+', shape=lat_arr.shape)
        lat_mmap[:] = lat_arr
        del lat_mmap

    if os.path.exists(lon_pathname):
        lon_mmap = np.memmap(lon_pathname, dtype=lon_arr.dtype, mode='r')
        if np.any(lon_mmap[:] != lon_arr):
            raise Exception('Expected longitude array to be the same')
    else:
        lon_mmap = np.memmap(lon_pathname, dtype=lon_arr.dtype, mode='w+', shape=lon_arr.shape)
        lon_mmap[:] = lon_arr
        del lon_mmap

    return data_basename, lat_basename, lon_basename

def fetch_monthly_normals(dataset_record, lat, lon):
    '''
    Fetches the monthly normals for the specified location.
    '''
    data_pathname = os.path.join(DATA_DIR, dataset_record['data_filename'])
    lat_pathname = os.path.join(DATA_DIR, dataset_record['lat_filename'])
    lon_pathname = os.path.join(DATA_DIR, dataset_record['lon_filename'])

    lat_mmap = np.memmap(lat_pathname, dtype=LAT_DTYPE, mode='r')
    lon_mmap = np.memmap(lon_pathname, dtype=LON_DTYPE, mode='r')

    lat_i = int(round((lat - dataset_record['lat_start']) / dataset_record['lat_delta']))
    actual_lat = lat_mmap[lat_i]
    lat_error = abs(dataset_record['lat_delta'] / 2)

    if abs(lat - actual_lat) >= lat_error:
        raise Exception('Expected latitude %g to be within %g of %g' % (lat, lat_error, actual_lat))

    lon_i = int(round((lon - dataset_record['lon_start']) / dataset_record['lon_delta']))
    actual_lon = lon_mmap[lon_i]
    lon_error = abs(dataset_record['lon_delta'] / 2)

    if abs(lon - actual_lon) >= lon_error:
        raise Exception('Expected longitude %g to be within %g of %g' % (lon, lon_error, actual_lon))

    data_mmap = np.memmap(data_pathname, dtype=DATA_DTYPE, mode='r',
                          shape=(MONTHS_PER_YEAR, lat_mmap.size, lon_mmap.size))

    normals_arr = np.ma.masked_values(data_mmap[:, lat_i, lon_i], dataset_record['fill_value'])

    if np.all(normals_arr.mask):
        raise NotFoundError('No data at %g, %g' % (actual_lat, actual_lon))

    return actual_lat, actual_lon, normals_arr

def fetch_normals_from_dataset(dataset_record, month):
    '''
    Fetches the data from the specified dataset record.
    Gives the data for the specified  month, returning a 2-D array indexed by latitude and longitude.
    '''
    data_pathname = os.path.join(DATA_DIR, dataset_record['data_filename'])
    lat_pathname = os.path.join(DATA_DIR, dataset_record['lat_filename'])
    lon_pathname = os.path.join(DATA_DIR, dataset_record['lon_filename'])

    lat_mmap = np.memmap(lat_pathname, dtype=LAT_DTYPE, mode='r')
    lon_mmap = np.memmap(lon_pathname, dtype=LON_DTYPE, mode='r')

    data_mmap = np.memmap(data_pathname, dtype=DATA_DTYPE, mode='r',
                          shape=(MONTHS_PER_YEAR, lat_mmap.size, lon_mmap.size))

    if np.any(data_mmap == dataset_record['fill_value']):
        data = np.ma.masked_values(data_mmap[month - 1, :], dataset_record['fill_value'])
    else:
        data = data_mmap[month - 1, :]

    return lat_mmap, lon_mmap, data

def fetch_normals_from_dataset_mean(dataset_record):
    '''
    Fetches the data from the specified dataset record.
    Averages the data over all months to return a 2-D array indexed by latitude and longitude
    with the means for the entire year.
    '''
    data_pathname = os.path.join(DATA_DIR, dataset_record['data_filename'])
    lat_pathname = os.path.join(DATA_DIR, dataset_record['lat_filename'])
    lon_pathname = os.path.join(DATA_DIR, dataset_record['lon_filename'])

    lat_mmap = np.memmap(lat_pathname, dtype=LAT_DTYPE, mode='r')
    lon_mmap = np.memmap(lon_pathname, dtype=LON_DTYPE, mode='r')

    data_mmap = np.memmap(data_pathname, dtype=DATA_DTYPE, mode='r',
                          shape=(MONTHS_PER_YEAR, lat_mmap.size, lon_mmap.size))

    data_mean = np.round(data_mmap.mean(axis = 0)).astype(DATA_DTYPE)

    if np.any(data_mmap == dataset_record['fill_value']):
        data = np.ma.masked_values(data_mean, dataset_record['fill_value'])
    else:
        data = data_mean

    return lat_mmap, lon_mmap, data

def wait_search(seconds):
    '''
    Waits the specified number of seconds to do another search.
    If other users are already requesting a search, we must wait
    the specified amount of time after ALL users have made the
    request.
    '''
    original_timestamp = timestamp = datetime.now().timestamp()
    total_delay = current_delay = 0
    queue_id = insert_search_queue(timestamp)
    commit()
    last_queue_id = next_queue_id = fetch_search_queue()

    while (next_queue_id != queue_id) or current_delay < seconds:
        time.sleep(seconds / 4)
        next_queue_id = fetch_search_queue()

        if total_delay >= 10:
            delete_search_queue(queue_id)
            raise Exception('Search queue timed out')

        if last_queue_id != next_queue_id:
            last_queue_id = next_queue_id
            timestamp = datetime.now().timestamp()

        current_delay = datetime.now().timestamp() - timestamp
        total_delay = datetime.now().timestamp() - original_timestamp

    delete_search_queue(queue_id)
    commit()

def insert_search_queue(timestamp):
    '''
    Inserts a search queue item with the specified timestamp.
    '''
    db.cur.execute(
        '''
        INSERT INTO search_queue(timestamp)
        VALUES (%s)
        ''',
        (timestamp,)
    )

    db.cur.execute(
        '''
        SELECT id FROM search_queue
        WHERE timestamp = %s
        ''',
        (timestamp,)
    )

    row = db.cur.fetchone()

    if row is None:
        raise Exception('Could not retrieve queue item with timestamp %g we just inserted' % timestamp)

    return row[0]

def fetch_search_queue():
    '''
    Fetches the id of the oldest item on the queue, or None if there are none.
    '''
    db.cur.execute(
        '''
        SELECT id FROM search_queue
        ORDER BY timestamp LIMIT 1
        '''
    )

    row = db.cur.fetchone()

    if row is None:
        return None
    else:
        return row[0]

def delete_search_queue(queue_id):
    '''
    Deletes the queue item with the specified id
    '''
    db.cur.execute(
        '''
        DELETE FROM search_queue
        WHERE id = %s
        ''',
        (queue_id,)
    )

def delete_geonames():
    '''
    Deletes all geonames.
    '''
    db.cur.execute('TRUNCATE geonames')

def create_geoname(geonameid, name, lat, lon, country, population, elevation):
    '''
    Creates a geoname entry.
    '''
    db.cur.execute(
        '''
        INSERT INTO geonames(geonameid, name, latitude, longitude, country, population, elevation)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''',
        (geonameid, name, lat, lon, country, population, elevation)
    )
