/**
 * Functions for showing the climate tiles over the base map.
 *
 * Copyright (c) 2020 Carlos Torchia
 */

import { showError } from './error.js';
import { dataSourceMaxZoomLevel, dataSourceAttribution } from './data-sources.js';

import CONFIG from '../config/config.json';
import APP from './app.js';

const TILE_ERROR_MESSAGE = 'Could not fetch climate map overlay. Please try again later.';

const ALLOWED_TILE_FORMATS = ['png'];

if (ALLOWED_TILE_FORMATS.indexOf(CONFIG.climate_tile_layer.format) === -1) {
    throw Error('Climate tile format is not valid.');
}

/**
 * Returns the climate tile URL for the specified dataset.
 */
function climateTileUrl(data_source, date_range, measurement, period)
{
    return CONFIG.climate_tile_layer.url + '/' +
        encodeURIComponent(data_source) + '/' +
        encodeURIComponent(date_range) + '/' +
        encodeURIComponent(measurement + '-' + period) +
        '/{z}/{x}/{y}.' + CONFIG.climate_tile_layer.format;
}

/**
 * Returns the climate tile URL for the selected dataset.
 */
function getClimateTileUrl()
{
    const data_source = document.getElementById('data-source').value;
    const date_range = document.getElementById('date-range').value;
    const measurement = document.getElementById('measurement').value;
    const period = document.getElementById('period').value;

    return climateTileUrl(data_source, date_range, measurement, period);
}


/**
 * Updates the tile layer for the climate filters in the document.
 */
export function updateClimateTileLayer(tile_layer)
{
    const data_source_select = document.getElementById('data-source');

    APP.attribution = dataSourceAttribution(data_source_select);

    tile_layer.remove();

    tile_layer.setUrl(getClimateTileUrl());
    tile_layer.options.attribution = 'Climate data: ' + APP.attribution;
    tile_layer.options.maxNativeZoom = dataSourceMaxZoomLevel(data_source_select);

    tile_layer.addTo(APP.climate_map);
}

/**
 * Creates an tile layer with climate data based on the inputs.
 * This shows the differences between different regions' climates in a visual way.
 *
 * @return map layer
 */
export function createClimateTileLayer()
{
    const data_source_select = document.getElementById('data-source');
    const max_zoom_level = dataSourceMaxZoomLevel(data_source_select);

    APP.attribution = dataSourceAttribution(data_source_select);

    const tile_layer = L.tileLayer(
        getClimateTileUrl(),
        {
            attribution: 'Climate data: ' + APP.attribution,
            zIndex: CONFIG.climate_tile_layer.z_index,
            maxNativeZoom: max_zoom_level,
            opacity: CONFIG.climate_tile_layer.opacity,
        }
    );

    tile_layer.on('tileerror', function() {
        showError(TILE_ERROR_MESSAGE);
    });

    return tile_layer;
}

/**
 * Show the basemaps defined in the config file.
 */
export function createBaseMapLayer()
{
    for (let i = 0; i <= CONFIG.tile_layers.length - 1; i++) {
        const tile_layer = CONFIG.tile_layers[i];

        if (tile_layer.mapboxGL) {
            try {
                L.mapboxGL({
                    attribution: tile_layer.attribution,
                    accessToken: tile_layer.access_token,
                    style: tile_layer.style_url,
                    zIndex: tile_layer.z_index,
                }).addTo(APP.climate_map);
            } catch (err) {
                showError('Error loading map tiles: ' + err.message);
                throw err;
            }
        } else {
            L.tileLayer(tile_layer.url, {
                attribution: tile_layer.attribution,
                zIndex: tile_layer.z_index,
                maxNativeZoom: tile_layer.max_zoom,
            }).addTo(APP.climate_map);
        }
    }
}
