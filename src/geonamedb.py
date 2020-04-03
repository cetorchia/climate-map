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

def fetch_populous_places_within_area(min_lat, max_lat, min_lon, max_lon):
    '''
    Fetches the top 20 populated cities in the specified area.
    '''
    # If the antimeridian (longitude 180) is contained within
    # the viewport, we have to reverse the comparison in order
    # not end up excluding the area we are trying to include.
    # The formula below is just the minimum longitude from 0 to 360
    # plus the distance between min and max longitude. If this
    # is greater than 360, the max longitude is passing the antimeridian.
    if (min_lon + 180) % 360 + max_lon - min_lon <= 360:
        lon_sql = 'AND longitude >= %s AND longitude < %s'
    else:
        lon_sql = 'AND (longitude < %s OR longitude >= %s)'

    climatedb.db.cur.execute(
        '''
        SELECT geonameid, name, latitude, longitude, country, province, population, elevation
        FROM geonames
        WHERE feature_class = 'P'
        AND latitude >= %s AND latitude < %s
        ''' + lon_sql + '''
        ORDER BY population DESC
        LIMIT 20
        ''',
        (min_lat, max_lat, (min_lon + 180) % 360 - 180, (max_lon + 180) % 360 - 180)
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
