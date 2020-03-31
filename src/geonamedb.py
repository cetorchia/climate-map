#!/usr/bin/env python3
#
# Geonames database
#
# Please read https://download.geonames.org/export/dump/ for
# detailed technical information about this data.
#
# Copyright (c) 2020 Carlos Torchia
#

import climatedb
from climatedb import NotFoundError

def search_geoname(query):
    '''
    Searches for a geoname matching the specified query.
    '''
    query = query.replace(',', '')

    try:
        return fetch_geoname(query)
    except NotFoundError as e:
        if query.find(' ') != -1:
            rest_of_name, area = query.rsplit(' ', 1)

            provinces = fetch_provinces_by_alternate_name(area)

            for province in provinces:
                province_code = province['code']
                country_code = province['country']
                try:
                    return fetch_geoname(rest_of_name, province_code, country_code)
                except NotFoundError as e:
                    pass

            countries = fetch_countries_by_alternate_name(area)

            for country in countries:
                province_code = None
                country_code = country['code']
                try:
                    return fetch_geoname(rest_of_name, province_code, country_code)
                except NotFoundError as e:
                    pass

    raise NotFoundError('Could not find "%s" in geonames' % query)

def delete_geonames():
    '''
    Deletes all geonames.
    '''
    climatedb.db.cur.execute('DELETE FROM geonames')

def create_geoname(geonameid, name, lat, lon, feature_class, feature_code, country, province, population, elevation):
    '''
    Creates a geoname entry.
    '''
    climatedb.db.cur.execute(
        '''
        INSERT INTO geonames(
            geonameid,
            name,
            latitude,
            longitude,
            feature_class,
            feature_code,
            country,
            province,
            population,
            elevation)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''',
        (geonameid, name, lat, lon, feature_class, feature_code, country, province, population, elevation)
    )

def fetch_geoname(name, province=None, country=None):
    '''
    Fetches the most populous geoname with the specified name.
    '''
    province_sql = 'AND province = %s' if province else ''
    province_params = (province,) if province else ()

    country_sql = 'AND country = %s' if country else ''
    country_params = (country,) if country else ()

    climatedb.db.cur.execute(
        '''
        SELECT
            geonameid,
            name,
            latitude,
            longitude,
            feature_class,
            feature_code,
            country,
            province,
            population,
            elevation
        FROM geonames
        WHERE name = %s
        ''' + province_sql + '''
        ''' + country_sql + '''
        ORDER BY population DESC
        LIMIT 1
        ''',
        (name,) + province_params + country_params
    )

    row = climatedb.db.cur.fetchone()

    if not row:
        raise NotFoundError('Could not fetch geoname %s' % name)

    (
        geonameid,
        name,
        latitude,
        longitude,
        feature_class,
        feature_code,
        country,
        province,
        population,
        elevation
    ) = row

    return {
        'geonameid': geonameid,
        'name': name,
        'latitude': latitude,
        'longitude': longitude,
        'feature_class': feature_class,
        'feature_code': feature_code,
        'country': country,
        'province': province,
        'population': population,
        'elevation': elevation
    }

def fetch_abbreviation_by_geoname(geonameid):
    '''
    Fetches the abbreviation of the specified geoname.
    '''
    climatedb.db.cur.execute(
        '''
        SELECT alternate_name
        FROM alternate_names
        WHERE geonameid = %s
        AND lang = 'abbr'
        LIMIT 1
        ''',
        (geonameid,)
    )

    row = climatedb.db.cur.fetchone()

    if not row:
        raise NotFoundError('Could not fetch alternate name of geoname %d' % geonameid)

    (alternate_name,) = row

    return alternate_name

def delete_countries():
    '''
    Deletes all countries
    '''
    climatedb.db.cur.execute('DELETE FROM countries')

def create_country(code, name, geonameid):
    '''
    Creates a country with the specified ISO code and name.
    '''
    climatedb.db.cur.execute(
        '''
        INSERT INTO countries(code, name, geonameid)
        VALUES (%s, %s, %s)
        ''',
        (code, name, geonameid)
    )

def fetch_geoname_by_country(code):
    '''
    Fetches the geoname of the country
    '''
    climatedb.db.cur.execute(
        '''
        SELECT g.geonameid, g.name, g.latitude, g.longitude, g.country, g.province, g.population, g.elevation
        FROM countries AS c
        INNER JOIN geonames AS g ON c.geonameid = g.geonameid
        WHERE c.code = %s
        ''',
        (code,)
    )

    row = climatedb.db.cur.fetchone()

    if not row:
        raise NotFoundError('Could not fetch geoname for country %s' % code)

    (
        geonameid,
        name,
        latitude,
        longitude,
        country,
        province,
        population,
        elevation
    ) = row

    return {
        'geonameid': geonameid,
        'name': name,
        'latitude': latitude,
        'longitude': longitude,
        'country': country,
        'province': province,
        'population': population,
        'elevation': elevation
    }

def fetch_countries_by_alternate_name(name):
    '''
    Fetches the countries with the specified alternate name.
    '''
    climatedb.db.cur.execute(
        '''
        SELECT c.code, c.name, c.geonameid
        FROM countries AS c
        LEFT JOIN alternate_names AS a ON a.geonameid = c.geonameid AND a.abbrev
        WHERE (c.name = %s OR c.code = %s OR a.alternate_name = %s)
        ''',
        (name, name, name)
    )

    rows = climatedb.db.cur.fetchall()

    return (
        {
            'code': code,
            'name': name,
            'geonameid': geonameid,
        }
        for code, name, geonameid
        in rows
    )



def delete_provinces():
    '''
    Deletes all provinces
    '''
    climatedb.db.cur.execute('DELETE FROM provinces')

def create_province(code, name, country, geonameid):
    '''
    Creates a province with the specified admin code and name.
    '''
    climatedb.db.cur.execute(
        '''
        INSERT INTO provinces(province_code, name, country, geonameid)
        VALUES (%s, %s, %s, %s)
        ''',
        (code, name, country, geonameid)
    )

def fetch_geoname_by_province(province_code, country):
    '''
    Fetches the geoname of the specified province.
    '''
    climatedb.db.cur.execute(
        '''
        SELECT g.geonameid, g.name, g.latitude, g.longitude, g.country, g.province, g.population, g.elevation
        FROM geonames AS g
        INNER JOIN provinces AS p ON p.geonameid = g.geonameid
        WHERE p.province_code = %s AND p.country = %s
        ''',
        (province_code, country)
    )

    row = climatedb.db.cur.fetchone()

    if not row:
        raise NotFoundError('Could not fetch geoname for province %s.%s' % (province_code, country))

    (
        geonameid,
        name,
        latitude,
        longitude,
        country,
        province,
        population,
        elevation
    ) = row

    return {
        'geonameid': geonameid,
        'name': name,
        'latitude': latitude,
        'longitude': longitude,
        'country': country,
        'province': province,
        'population': population,
        'elevation': elevation
    }

def fetch_provinces_by_alternate_name(name):
    '''
    Fetches the provinces with the specified alternate name.
    '''
    climatedb.db.cur.execute(
        '''
        SELECT p.province_code, p.name, p.country, p.geonameid
        FROM provinces AS p
        LEFT JOIN alternate_names AS a ON a.geonameid = p.geonameid AND abbrev
        WHERE (p.name = %s OR a.alternate_name = %s)
        ''',
        (name, name)
    )

    rows = climatedb.db.cur.fetchall()

    return (
        {
            'code': code,
            'name': name,
            'country': country,
            'geonameid': geonameid,
        }
        for code, name, country, geonameid
        in rows
    )

def delete_alternate_names():
    '''
    Deletes all alternate names
    '''
    climatedb.db.cur.execute('DELETE FROM alternate_names')

def create_alternate_name(alternate_name_id, geonameid, lang, alternate_name, preferred, abbrev):
    '''
    Creates an alternate name entry to say that a specified geoname has
    the specified alternate name.
    '''
    climatedb.db.cur.execute(
        '''
        INSERT INTO alternate_names(id, geonameid, lang, alternate_name, preferred, abbrev)
        VALUES (%s, %s, %s, %s, %s, %s)
        ''',
        (alternate_name_id, geonameid, lang, alternate_name, preferred, abbrev)
    )

def fetch_geonames_population_over(min_population):
    '''
    Gives geonames which have a population of at least the specified minimum.
    Sorts by population in ascending order because then the user will see
    more populous places instead of less populous places.

    Countries and provinces are excluded.
    '''
    climatedb.db.cur.execute(
        '''
        SELECT geonameid, name, latitude, longitude, country, province, population, elevation
        FROM geonames
        WHERE feature_code = 'PPLC'
        OR (population > %s AND feature_class = 'P')
        ORDER BY population ASC
        ''',
        (min_population,)
    )

    rows = climatedb.db.cur.fetchall()

    return (
        {
            'geonameid': geonameid,
            'name': name,
            'latitude': latitude,
            'longitude': longitude,
            'country': country,
            'province': province,
            'population': population,
            'elevation': elevation
        }
        for geonameid,
            name,
            latitude,
            longitude,
            country,
            province,
            population,
            elevation
        in rows
    )

def places_by_latitude_and_longitude(min_population):
    '''
    Gives all geonames with at least the specified population,
    indexed by latitude and longitude.

    This dict will be indexed by integer, and it will have
    'lat_start', 'lat_delta', 'lon_start', and 'lon_delta' keys, and
    these can tell you how to fetch the place by its latitude and
    longitude. If two places map to the same coordinates, the
    one with higher population will be taken.
    '''
    LAT_START = 90
    LAT_DELTA = -5
    LON_START = -180
    LON_DELTA = 5

    geonames = fetch_geonames_population_over(min_population)

    output = {
        'lat_start': LAT_START,
        'lat_delta': LAT_DELTA,
        'lon_start': LON_START,
        'lon_delta': LON_DELTA,
        'geonames': {},
    }

    for geoname in geonames:
        i = int(round((geoname['latitude'] - LAT_START) / LAT_DELTA))
        j = int(round((geoname['longitude'] - LON_START) / LON_DELTA))

        if output['geonames'].get(i) is None:
            output['geonames'][i] = {}

        output['geonames'][i][j] = {
            'name': geoname['name'],
            'geonameid': geoname['geonameid'],
            'latitude': geoname['latitude'],
            'longitude': geoname['longitude'],
        }

    return output
