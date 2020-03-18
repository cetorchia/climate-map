#!/usr/bin/env python3
#
# Transforms dataset files to various data formats for use
# as climate data.
#
# Copyright (c) 2020 Carlos Torchia
#
import os
import sys
_dir_path = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'src')
sys.path.append(_dir_path)

from datetime import date

import transform
import climatedb
import geo
import tiling

def get_args(arguments):
    '''
    Determines command line arguments
    '''
    if len(arguments) < 5:
        print('Usage: ' + arguments[0] + ' [options] <data-source> <variable> <start-year> <end-year>', file=sys.stderr)
        print('Options:', file=sys.stderr)
        print('  --calibrated   Whether to generate tiles for the calibrated version of this dataset', file=sys.stderr)
        print('  --single-image Whether generate one large image instead of tiles', file=sys.stderr)
        sys.exit(1)

    options = arguments[1:-4]
    rest_of_arguments = arguments[-4:]

    data_source = rest_of_arguments[0]
    variable_name = rest_of_arguments[1]
    start_year = int(rest_of_arguments[2])
    end_year = int(rest_of_arguments[3])

    start_date = date(start_year, 1, 1)
    end_date = date(end_year, 12, 31)

    calibrated = True if '--calibrated' in options else False
    single_image = True if '--single-image' in options else False

    return data_source, variable_name, start_date, end_date, calibrated, single_image

def tile_folder(data_source, variable_name, start_date, end_date, months=None):
    '''
    Gives the directory where tiles will be stored.
    '''
    repo = os.path.dirname(os.path.dirname(__file__))
    date_range = '%d-%d' % (start_date.year, end_date.year)

    if months:
        period = '%02d_%02d_%02d' % months
    else:
        period = 'year'

    tile_folder = os.path.join(repo, 'public', 'tiles', data_source, date_range, variable_name + '-' + period)

    return tile_folder

def main(args):
    '''
    The main function
    '''
    data_source, variable_name, start_date, end_date, calibrated, single_image = get_args(args)

    measurement = transform.to_standard_variable_name(variable_name)
    units = transform.standard_units_from_measurement(measurement)

    climatedb.connect()

    unit_id = climatedb.fetch_unit(units)['id']
    measurement_id = climatedb.fetch_measurement(measurement)['id']
    data_source_record = climatedb.fetch_data_source(data_source)

    dataset = climatedb.fetch_dataset(
        data_source_record['id'],
        measurement_id,
        unit_id,
        start_date,
        end_date,
        calibrated=True if calibrated else False
    )

    print(data_source, measurement, start_date.year, end_date.year, 'year')
    lat_arr, lon_arr, normals = climatedb.fetch_normals_from_dataset_mean(dataset)

    projected_y_arr = geo.lat2y(lat_arr)
    projected_x_arr = geo.lon2x(lon_arr)

    output_folder = tile_folder(data_source, variable_name, start_date, end_date)
    transform.save_contours_tiles(
        projected_y_arr,
        projected_x_arr,
        units,
        normals,
        output_folder,
        data_source_record['id'],
        tile=not single_image
    )

    for start_month in (12, 3, 6, 9):
        months = start_month, (start_month + 1) % 12, (start_month + 2) % 12
        print(data_source, measurement, start_date.year, end_date.year, months)

        aggregated_normals = None

        for month in months:
            lat_arr, lon_arr, normals = climatedb.fetch_normals_from_dataset(dataset, month)
            if aggregated_normals is None:
                aggregated_normals = normals.copy()
            else:
                aggregated_normals += normals

        aggregated_normals = aggregated_normals / len(months)

        output_folder = tile_folder(data_source, variable_name, start_date, end_date, months)

        tiling.save_contours_tiles(
            projected_y_arr,
            projected_x_arr,
            units,
            aggregated_normals,
            output_folder,
            data_source_record['id'],
            tile=not single_image
        )

    climatedb.close()

if __name__ == '__main__':
    sys.exit(main(sys.argv))
