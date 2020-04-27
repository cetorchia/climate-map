#!/usr/bin/env python3
#
# Downloads the specified climate dataset off the internet.
#
# Copyright (c) 2020 Carlos Torchia
#
import os
import sys
_dir_path = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'src')
sys.path.append(_dir_path)

import ssl
import urllib.request
import urllib.parse
import yaml
import json
import xml.etree.ElementTree

import climatedb

DATASET_DIR_NAME = 'datasets'
CONFIG_DIR_NAME = 'config'
CONFIG_FILENAME = 'config-esgf.yaml'
SEARCH_FORMAT = 'application/solr+json'

def get_args(arguments):
    '''
    Determines command line arguments
    '''
    num_arguments = len(arguments)

    if num_arguments < 3 or num_arguments > 4:
        print('Usage: ' + arguments[0] + ' <data-source> <var> [frequency]', file=sys.stderr)
        print('e.g. ' + arguments[0] + ' TerraClimate pet', file=sys.stderr)
        print('e.g. ' + arguments[0] + ' GFDL-ESM4.historical tas day', file=sys.stderr)
        sys.exit(1)

    data_source, variable_name = arguments[1:3]

    frequency = arguments[3] if len(arguments) >= 4 else 'mon'

    return variable_name, data_source, frequency

def load_config():
    '''
    Loads the config variables
    '''
    config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), CONFIG_DIR_NAME)
    config_file = os.path.join(config_dir, CONFIG_FILENAME)

    with open(config_file, 'r') as f:
        yaml_data = yaml.load(f)

    return yaml_data

def search_esgf(search_url, project, variable_name, model, scenario, frequency, variant):
    '''
    Searches for the specified dataset in the ESGF database.
    '''
    search_parameters = {
        'offset': 0,
        'limit': 1,
        'type': 'Dataset',
        'replica': 'false',
        'latest': 'true',
        'source_id': model,
        'project': project,
        'variable_id': variable_name,
        'experiment_id': scenario,
        'variant_label': variant,
        'frequency': frequency,
        'format': SEARCH_FORMAT,
    }

    url = search_url + '?' + urllib.parse.urlencode(search_parameters)

    ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    res = urllib.request.urlopen(url, context=ssl_ctx)

    if res.code >= 400:
        raise Exception('Could not search for dataset: %d %s' % (res.code, res.reason))

    data = json.load(res)

    return data

def get_citation(url):
    '''
    Fetches citation details from the specified URL
    '''
    ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    res = urllib.request.urlopen(url, context=ssl_ctx)

    if res.code >= 400:
        raise Exception('Could not fetch citation info: %d %s' % (res.code, res.reason))

    data = json.load(res)

    author = '; '.join(creator['creatorName'] for creator in data['creators'][:3])

    if len(data['creators']) > 3:
        author += ' et al.'

    if data['identifier']['identifierType'] != 'DOI':
        raise Exception('Expected DOI in citation, got ' + data['identifier']['identifierType'])

    article_url = 'http://doi.org/' + data['identifier']['id']

    year = data['publicationYear']

    return author, year, article_url

def create_data_source(data_source_code, organisation, author, year, url):
    '''
    Creates the data source record in the database if one
    does not exist.
    '''
    if data_source_code.find('.') != -1:
        model, scenario = data_source_code.split('.')

        if scenario == 'ssp245':
            name = model + ' middle of the road'
        elif scenario == 'ssp585':
            name = model + ' fossil fueled development'
        else:
            name = model + ' ' + scenario

    else:
        name = data_source_code

    if data_source_code in ('TerraClimate', 'worldclim'):
        baseline = True
    else:
        baseline = False

    try:
        climatedb.fetch_data_source(data_source_code)
        climatedb.update_data_source(data_source_code, name, organisation, author, year, url, baseline)

    except climatedb.NotFoundError:
        climatedb.create_data_source(data_source_code, name, organisation, author, year, url, baseline)

    climatedb.commit()

def get_thredds_url(dataset_info):
    '''
    Gives the THREDDS URL for the specified dataset.
    Also returns the ID that you must look for in the THREDDS
    XML response to get the HTTP file URL.
    (They can't just have a link to the file in there, can they?)
    '''
    for url in dataset_info['url']:
        # And this can't just be a JSON object?
        actual_url, content_type, url_type = url.split('|')
        if url_type == 'THREDDS':
            thredds_url, thredds_id = actual_url.split('#')
            return thredds_url, thredds_id

    raise Exception('No THREDDS URL in this dataset. Change the code here to get the dataset some other way.')

def get_file_url(thredds_url, thredds_id):
    '''
    Fetches the specified THREDDS dataset and returns
    the URL to the file itself.
    '''
    ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    res = urllib.request.urlopen(thredds_url, context=ssl_ctx)

    if res.code >= 400:
        raise Exception('Could not fetch dataset from THREDDS: %d %s' % (res.code, res.reason))

    xml_root = xml.etree.ElementTree.parse(res)

    # Retrieve the first dataset in the list. (They may be broken down by different date ranges.)
    ns = {'catalog': 'http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0'}
    dataset_element = xml_root.find('catalog:dataset[@ID=\'%s\']/catalog:dataset' % thredds_id, ns)
    service_element = xml_root.find('catalog:service/*[@serviceType=\'HTTPServer\']', ns)

    p = urllib.parse.urlparse(thredds_url)
    url = p.scheme + '://' + p.netloc + service_element.get('base') + dataset_element.get('urlPath')

    return url

def get_file_path(file_url):
    '''
    Gives the expected file path from the specified file URL.
    '''
    file_basename = file_url.split('/')[-1]
    file_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), DATASET_DIR_NAME)
    file_pathname = os.path.join(file_dir, file_basename)

    return file_pathname

def main(args):
    '''
    The main function
    '''
    climatedb.connect()

    variable_name, data_source, frequency = get_args(args)

    if data_source == 'TerraClimate':
        # This will have to be updated manually, as this is not
        # in machine-readable format anywhere.
        organisation = 'TerraClimate'
        author = 'Abatzoglou, J.T., S.Z. Dobrowski, S.A. Parks, K.C. Hegewisch'
        year = '2018'
        article_url = 'https://doi.org/10.1038/sdata.2017.191'
        start_year = 1981
        end_year = 2010

        if variable_name == 'elevation':
            file_url = 'http://thredds.northwestknowledge.net:8080/thredds/fileServer/TERRACLIMATE_ALL/layers/terraclim_dem.nc'
        else:
            file_url = 'http://thredds.northwestknowledge.net:8080/thredds/fileServer/TERRACLIMATE_ALL/summaries/' \
                       'TerraClimate%d%d_%s.nc' % (start_year, end_year, variable_name)

    elif data_source == 'worldclim':
        raise Exception('TODO: implement fetching worldclim dataset')

    else:
        model, scenario = data_source.split('.')

        config = load_config()
        search_url = config['search']['url']
        project = config['search']['project']
        variant = config['search']['variant']

        search_results = search_esgf(search_url, project, variable_name, model, scenario, frequency, variant)

        datasets = search_results['response']['docs']
        datasets.sort(key=lambda dataset: dataset['variant_label'])

        if len(datasets) == 0:
            raise Exception('No datasets in response')

        dataset_info = search_results['response']['docs'][0]

        organisation = dataset_info['institution_id'][0]
        author, year, article_url = get_citation(dataset_info['citation_url'][0])

        thredds_url, thredds_id = get_thredds_url(dataset_info)
        file_url = get_file_url(thredds_url, thredds_id)

    file_path = get_file_path(file_url)

    if not os.path.exists(file_path):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        urllib.request.urlretrieve(file_url, file_path)

    create_data_source(data_source, organisation, author, year, article_url)

if __name__ == '__main__':
    sys.exit(main(sys.argv))
