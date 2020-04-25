#!/usr/bin/env python3
#
# This generates map tiles that go underneath the climate
# colour map. This is different from generating climate tiles.
# This generates map tiles that have data such as cities, lakes,
# ocean, etc.
#
# This also retrieves the Natural Earth Data into the datasets
# folder if they do not exist. To keep it up to date, you can
# optionally remove this folder yourself: datasets/natural-earth.
# This will trigger a download of the new data.
#
# However, existing tiles will be overwritten regardless if
# they exist.
#
import os
import sys

__DIR__ = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(os.path.join(__DIR__, 'vendor'))

import shutil
from zipfile import ZipFile
import urllib.request
import xml.etree.ElementTree

from generate_tiles import render_tiles


DATASETS_SUBDIR = os.path.join('datasets', 'natural-earth')
DATASETS_DIR = os.path.join(__DIR__, DATASETS_SUBDIR)

STYLESHEET = os.path.join(__DIR__, 'mapnik-style.xml')
TILE_DIR = os.path.join(__DIR__, 'public', 'map-tiles') + os.path.sep

BBOX = (-180.0,-90.0, 180.0,90.0)

BASE_URL = 'https://www.naturalearthdata.com/http//www.naturalearthdata.com/download'


def get_args(arguments):
    '''
    Determines command line arguments
    '''
    if len(arguments) != 3:
        print('Usage: ' + arguments[0] + ' <min-zoom> <max-zoom>', file=sys.stderr)
        sys.exit(1)

    min_zoom, max_zoom = arguments[1:3]

    return int(min_zoom), int(max_zoom)

def get_shapefiles():
    '''
    Gives the list of files required from the stylesheet.
    '''
    with open(STYLESHEET, 'r') as f:
        xml_root = xml.etree.ElementTree.parse(f)
        file_elements = xml_root.findall('Layer/Datasource/Parameter[@name="file"]')

        for file_element in file_elements:
            shapefile = file_element.text
            yield shapefile

def get_zip_filename(shapefile):
    '''
    Gives the zip filename from the specified shapefile.
    Mapnik has to be able to access the shapefile, so the
    path must be relative to the main directory. So we have
    to remove the part of the path that is different from
    what's on the Natural Earth Data server.
    '''
    zip_file = shapefile.rsplit('.', 1)[0] + '.zip'
    zip_parts = zip_file.split(os.path.sep)
    expected_parents = DATASETS_SUBDIR.split(os.path.sep)

    if zip_parts[:len(expected_parents)] != expected_parents:
        raise Exception('Expected %s to be relative to %s' % (shapefile, DATASETS_SUBDIR))

    return os.path.join(*zip_parts[len(expected_parents):])

def update_data():
    '''
    Ensure that the shapefiles exist.
    '''
    os.makedirs(os.path.dirname(DATASETS_DIR), exist_ok=True)

    for shapefile in get_shapefiles():
        zip_file = get_zip_filename(shapefile)
        zip_file_url = BASE_URL + '/' + zip_file
        zip_file_path = os.path.join(DATASETS_DIR, zip_file)
        zip_file_dirname = os.path.dirname(zip_file_path)

        if not os.path.exists(zip_file_path):
            print('Updating ' + zip_file_path)
            os.makedirs(zip_file_dirname, exist_ok=True)
            urllib.request.urlretrieve(zip_file_url, zip_file_path)

        with ZipFile(zip_file_path, 'r') as zf:
            zf.extractall(zip_file_dirname)

            if zf.infolist()[0].is_dir():
                subdir = zf.infolist()[0].filename
                subdir_path = os.path.join(zip_file_dirname, subdir)

                for file in os.listdir(subdir_path):
                    os.replace(os.path.join(subdir_path, file), os.path.join(zip_file_dirname, file))

                os.rmdir(subdir_path)

def rm_zoom_levels(min_zoom, max_zoom):
    '''
    Removes all map tiles within the specified zoom levels.
    Map tiles not within the specified zoom levels will remain intact.
    '''
    for zoom_level in range(min_zoom, max_zoom + 1):
        zoom_path = os.path.join(TILE_DIR, str(zoom_level))

        if os.path.exists(zoom_path):
            shutil.rmtree(zoom_path)

def main(args):
    '''
    The main function
    '''
    min_zoom, max_zoom = get_args(args)

    update_data()

    rm_zoom_levels(min_zoom, max_zoom)

    render_tiles(BBOX, STYLESHEET, TILE_DIR, min_zoom, max_zoom, 'World')

if __name__ == '__main__':
    sys.exit(main(sys.argv))
