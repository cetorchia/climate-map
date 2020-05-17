/**
 * Search
 *
 * Copyright (c) 2020 Carlos Torchia
 */

import { search } from './api.js';
import { getPlaceName } from './places.js';
import { viewLocationClimate } from './charts.js';

import CONFIG from '../config/config.json';
import APP from './app.js';

/**
 * Searches for the location specified in the search box
 * and shows the climate of the location.
 */
export async function doSearch(search_query) {
    const geoname = await search(search_query);
    const lat = geoname['latitude'];
    const lon = geoname['longitude'];

    document.getElementById('search-container').style.display = 'none';

    APP.climate_map.setView([lat, lon], CONFIG.search_zoom);

    const place_name = getPlaceName(geoname);

    return [lat, lon, place_name];
}

/**
 * Handle search.
 */
export function handleSearch()
{
    const search_input = document.getElementById('search');

    function do_search(search_query) {
        if (search_query) {
            doSearch(search_query).then(([lat, lon, location_title]) => {
                viewLocationClimate(lat, lon, location_title);
            });
        }
    }

    document.getElementById('search-button').onclick = function() {
        do_search(search_input.value);
    };

    search_input.addEventListener('keyup', function(event) {
        /* Credit: https://www.w3schools.com/howto/howto_js_trigger_button_enter.asp */
        event.preventDefault();
        if (event.keyCode === 13) {
            do_search(search_input.value);
        }
    });

    document.getElementById('search-expand-button').onclick = function() {
        const search_div = document.getElementById('search-container');

        if (search_div.style.display == 'none') {
            search_div.style.display = 'block';
            const search_input = document.getElementById('search');
            search_input.focus();
            search_input.setSelectionRange(0, search_input.value.length);
        } else {
            search_div.style.display = 'none';
        }
    };
}
