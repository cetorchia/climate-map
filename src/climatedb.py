#!/usr/bin/env python3
#
# Climate database
#
# Copyright (c) 2020 Carlos Torchia
#

import psycopg2
import psycopg2.extras
import re
import math
from datetime import datetime
import time

# Connection string is of the form "<host>:[<port>:]<dbname>:<user>"
CONN_STR_RE = re.compile('^([^:]+):(?:([0-9]+):)?([^:]+):([^:]+)$')

# Global database object
db = None

def connect(conn_str):
    '''
    Connects to the specified db
    '''
    global db

    if db is not None:
        db.conn.close()

    db = Db(conn_str)

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
    def __init__(self, conn_str):
        host, port, dbname, user = CONN_STR_RE.search(conn_str).groups()

        if port is None:
            dsn = 'host=%s dbname=%s user=%s' % (host, dbname, user)
        else:
            dsn = 'host=%s port=%d dbname=%s user=%s' % (host, port, dbname, user)

        self.conn = psycopg2.connect(dsn)
        self.cur = self.conn.cursor()

class NotFoundError(Exception):
    '''
    Thrown when a record is not found.
    '''
    pass

def fetch_data_source_by_id(data_source_id):
    '''
    Fetches the specified data source
    '''
    db.cur.execute(
        '''
        SELECT id, code, name, organisation, url, author, year
        FROM data_sources
        WHERE id = %s
        ''',
        (data_source_id,)
    )
    row = db.cur.fetchone()

    if row is None:
        raise NotFoundError('Could not find data source %d' % data_source_id)

    data_source_id, code, name, organisation, url, author, year = row

    return {
        'id': data_source_id,
        'code': code,
        'name': name,
        'organisation': organisation,
        'url': url,
        'author': author,
        'year': year,
    }

def fetch_data_source(data_source_code):
    '''
    Fetches the specified data source
    '''
    db.cur.execute(
        '''
        SELECT id, name, organisation, url, author, year
        FROM data_sources
        WHERE code = %s
        ''',
        (data_source_code,)
    )
    row = db.cur.fetchone()

    if row is None:
        raise NotFoundError('Could not find data source "%s"' % data_source_code)

    data_source_id, name, organisation, url, author, year = row

    return {
        'id': data_source_id,
        'code': data_source_code,
        'name': name,
        'organisation': organisation,
        'url': url,
        'author': author,
        'year': year,
    }

def fetch_date_ranges():
    '''
    Fetches all date ranges for available datasets in the system.
    '''
    db.cur.execute(
        '''
        SELECT date_part('year', start_date) AS start_year, date_part('year', end_date) AS end_year
        FROM datasets d
        INNER JOIN data_sources s ON s.id = d.data_source_id
        WHERE s.active
        GROUP BY 1, 2
        ORDER BY 1, 2
        '''
    )

    rows = db.cur.fetchall()

    return ['%d-%d' % (start_year, end_year) for start_year, end_year in rows]

def fetch_datasets_by_date_range(start_date, end_date):
    '''
    Fetches the datasets matching the specified date range.
    '''
    db.cur.execute(
        '''
        SELECT id, data_source_id FROM datasets
        WHERE start_date = %s AND end_date = %s
        ''',
        (start_date, end_date)
    )
    rows = db.cur.fetchall()

    return [
        {
            'id': dataset_id,
            'data_source_id': data_source_id,
            'start_date': start_date,
            'end_date': end_date,
        }
        for dataset_id, data_source_id in rows
    ]

def fetch_dataset(data_source_id, start_date, end_date):
    '''
    Fetches the dataset with the specified data source, start date, and end date.
    '''
    db.cur.execute(
        '''
        SELECT id, delta FROM datasets
        WHERE data_source_id = %s
        AND start_date = %s AND end_date = %s
        ''',
        (data_source_id, start_date, end_date)
    )
    row = db.cur.fetchone()

    if row is None:
        raise NotFoundError('Could not find dataset for data source %d, start_date %s, and end_date %s' % (
            data_source_id, start_date, end_date
        ))

    dataset_id, delta = row

    return {
        'id': dataset_id,
        'data_source_id': data_source_id,
        'start_date': start_date,
        'end_date': end_date,
        'delta': delta,
    }

def create_dataset(data_source_id, start_date, end_date, delta):
    '''
    Creates a new dataset for the specified data source, start date, and end date.
    '''
    db.cur.execute(
        '''
        INSERT INTO datasets(data_source_id, start_date, end_date, delta)
        VALUES (%s, %s, %s, %s)
        ''',
        (data_source_id, start_date, end_date, delta)
    )

    return fetch_dataset(data_source_id, start_date, end_date)

def fetch_unit(units):
    '''
    Fetches the specified units record using the specified units code (e.g. 'degC', 'mm').
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

def fetch_data_points(dataset_id):
    '''
    Fetches all data points in the specified dataset.
    '''
    db.cur.execute(
        '''
        SELECT id, ST_X(location) AS lon, ST_Y(location) AS lat
        FROM data_points
        WHERE dataset_id = %s
        ORDER BY lat DESC, lon
        ''',
        (dataset_id,)
    )

    rows = db.cur.fetchall()

    if rows is None:
        raise Exception('Could not fetch rows for dataset %d' % dataset_id)

    return rows

def fetch_data_point(dataset_id, lat, lon):
    '''
    Fetches the data point at the specified location
    '''
    db.cur.execute(
        '''
        SELECT id FROM data_points
        WHERE dataset_id = %s AND location = ST_MakePoint(%s, %s)
        ''',
        (dataset_id, lon, lat)
    )
    row = db.cur.fetchone()

    if row is None:
        raise NotFoundError('Could not find data point %d, (%.10f, %.10f)' % (dataset_id, lat, lon))

    data_point_id = row[0]

    return data_point_id

def create_data_point_batch(values):
    '''
    Creates a data point a the specified location
    Values must be tuples in the form (dataset_id, lat, lon).
    '''
    values_to_insert = ((dataset_id, lon, lat) for dataset_id, lat, lon in values)
    psycopg2.extras.execute_batch(
        db.cur,
        '''
        INSERT INTO data_points(dataset_id, location)
        VALUES (%s, ST_MakePoint(%s, %s))
        ''',
        values_to_insert
    )

def fetch_data_point_closest_to(dataset_id, lat, lon, error):
    '''
    Fetches the data point closest to the specified location
    '''
    db.cur.execute(
        '''
        SELECT id, ST_X(location) AS lon, ST_Y(location) AS lat
        FROM data_points
        WHERE dataset_id = %s
        AND location <-> ST_MakePoint(%s, %s) < %s
        ORDER BY location <-> ST_MakePoint(%s, %s) LIMIT 1
        ''',
        (dataset_id, lon, lat, error, lon, lat)
    )
    row = db.cur.fetchone()

    if row is None:
        raise NotFoundError('Could not find data point %d, (%.10f, %.10f)' % (dataset_id, lat, lon))

    data_point_id, actual_lon, actual_lat = row

    return {
        'id': data_point_id,
        'dataset_id': dataset_id,
        'lat': actual_lat,
        'lon': actual_lon,
    }

def create_monthly_normal_batch(values):
    '''
    Creates a monthly normal value for the specified data point
    '''
    psycopg2.extras.execute_values(
        db.cur,
        '''
        INSERT INTO monthly_normals(data_point_id, measurement_id, unit_id, month, value)
        VALUES %s
        ''',
        values
    )

def fetch_monthly_normals_by_data_point(data_point_id):
    '''
    Fetches all monthly normals for the specified data point.
    '''
    db.cur.execute(
        '''
        SELECT m.code, u.code, n.month, n.value
        FROM monthly_normals n
        INNER JOIN measurements m ON m.id = n.measurement_id
        INNER JOIN units u ON u.id = n.unit_id
        WHERE n.data_point_id = %s
        ''',
        (data_point_id,)
    )

    normals = {}

    for measurement, units, month, value in db.cur.fetchall():
        if normals.get(measurement) is None:
            normals[measurement] = {}
        normals[measurement][month] = [value, units]

    return normals

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

    print(total_delay)
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
