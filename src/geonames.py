#!/usr/bin/env python3
#
# Loads geonames files into the database.
#
# Please read https://download.geonames.org/export/dump/ for
# detailed technical information about this data.
#
# Copyright (c) 2020 Carlos Torchia
#
from MySQLdb import IntegrityError, DataError
import MySQLdb.constants.ER
import climatedb
import geonamedb

def load_geonames(filename):
    '''
    Loads the geonames from the specified file.
    See https://download.geonames.org/export/dump/ for export and documentation.
    '''
    with open(filename, encoding='utf-8') as f:
        geonamedb.delete_geonames()
        for line in f:
            row = line[:-1].split('\t')
            (
                geonameid,
                name,
                asciiname,
                alternatenames,
                latitude,
                longitude,
                feature_class,
                feature_code,
                country,
                cc2,
                admin1_code,
                admin2_code,
                admin3_code,
                admin4_code,
                population,
                elevation,
                dem,
                timezone,
                modification_date,
            ) = row

            province = None if admin1_code == '' else admin1_code
            country = None if country == '' else country
            population = None if population == '' else int(population)
            elevation = None if elevation == '' else int(elevation)

            try:
                geonamedb.create_geoname(
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
                )

            except IntegrityError as e:
                if e.args[0] == MySQLdb.constants.ER.NO_REFERENCED_ROW_2 \
                and e.args[1].find('FOREIGN KEY (`province`)') != -1:
                    geonamedb.create_geoname(
                        geonameid,
                        name,
                        latitude,
                        longitude,
                        feature_class,
                        feature_code,
                        country,
                        None,
                        population,
                        elevation
                    )
                else:
                    raise e

            except DataError as e:
                if e.args[0] == MySQLdb.constants.ER.DATA_TOO_LONG \
                and e.args[1] == 'Data too long for column \'province\' at row 1':
                    geonamedb.create_geoname(
                        geonameid,
                        name,
                        latitude,
                        longitude,
                        feature_class,
                        feature_code,
                        country,
                        None,
                        population,
                        elevation
                    )
                else:
                    raise e

    climatedb.commit()

def load_countries(filename):
    '''
    Loads country information from the specified file.
    '''
    with open(filename, encoding='utf-8') as f:
        geonamedb.delete_countries()
        for line in f:
            if line[0] != '#':
                row = line[:-1].split('\t')
                (
                    iso,
                    iso3,
                    iso_numeric,
                    fips,
                    name,
                    capital,
                    area_km2,
                    population,
                    continent,
                    tld,
                    currency_code,
                    currency_name,
                    phone,
                    postal_code_fmt,
                    postal_code_regex,
                    languages,
                    geonameid,
                    neighbours,
                    equivalent_fips,
                ) = row

                geonamedb.create_country(iso, name, geonameid)

        climatedb.commit()

def load_provinces(filename):
    '''
    Loads province information from the specified file.
    '''
    with open(filename, encoding='utf-8') as f:
        geonamedb.delete_provinces()

        for line in f:
            row = line[:-1].split('\t')
            (
                admin_code,
                utf8_name,
                ascii_name,
                geonameid,
            ) = row

            country, province_code = admin_code.split('.')

            geonamedb.create_province(province_code, utf8_name, country, geonameid)

        climatedb.commit()

def load_alternate_names(filename):
    '''
    Loads alternate name information from the specified file.
    '''
    with open(filename, encoding='utf-8') as f:
        geonamedb.delete_alternate_names()

        for line in f:
            row = line[:-1].split('\t')
            (
                alternate_name_id,
                geonameid,
                lang,
                alternate_name,
                preferred,
                is_short_name,
                colloquial,
                historic
            ) = row

            # Some records do not have "isShortName" enabled but lang is "abbr"
            # to indicate it's an abbreviation. I'll take it.
            preferred = True if preferred else False
            abbrev = True if lang == 'abbr' else False

            if not colloquial and not historic and abbrev:
                try:
                    geonamedb.create_alternate_name(
                        alternate_name_id,
                        geonameid,
                        lang,
                        alternate_name,
                        preferred,
                        abbrev
                    )
                except IntegrityError as e:
                    if e.args[0] == MySQLdb.constants.ER.NO_REFERENCED_ROW_2 \
                    and e.args[1].find('FOREIGN KEY (`geonameid`)') != -1:
                        print('Geoname ID %d is not found' % int(geonameid))
                    else:
                        raise e

        climatedb.commit()
