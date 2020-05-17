/**
 * Functions for updating the page state,
 * which is useful for updating the address bar
 * and making the back button go back within the app.
 *
 * Copyright (c) 2020 Carlos Torchia
 */

import { loadLocationClimate, hideClimateCharts } from './charts.js';
import { doSearch } from './search.js';

import APP from './app.js';

import { APP_URL, DEFAULT_PAGE_TITLE } from './app.js';

/**
 * Updates the state of the page. This will update the
 * URL given the current "location" in the app.
 */
export function updatePageState(lat, lon, location, page_title)
{
    const state = {
        location: location !== undefined ? location : null,
        page_title: page_title ? page_title : (location ? 'Climate of ' + location : DEFAULT_PAGE_TITLE),
        lat: lat !== undefined ? lat : null,
        lon: lon !== undefined ? lon : null,
    };

    let url_path;

    if (state.location !== null) {
        url_path = APP_URL + 'location/' + encodeURIComponent(state.location.replace(',', ''));
    } else if (state.lat !== null && state.lon !== null) {
        url_path = APP_URL + 'location/' + encodeURIComponent(state.lat) + '/' + encodeURIComponent(state.lon);
    } else {
        url_path = APP_URL;
    }

    document.title = state.page_title;
    window.history.pushState(state, state.page_title, url_path);
}

/**
 * Goes to the specified URL in the app.
 */
export function goToURL(url)
{
    const state = pageStateFromURL(url);
    goToPageState(state);
    window.history.replaceState(state, state.page_title);
}

export function goToPageState(state)
{
    if (state.lat !== null && state.lon !== null) {
        loadLocationClimate(state.lat, state.lon, state.location).then(function() {
            APP.climate_map.setView([state.lat, state.lon], APP.climate_map.options.maxZoom);
        });
    } else if (state.location !== null) {
        doSearch(state.location).then(([lat, lon, location_title]) => {
            loadLocationClimate(lat, lon, location_title);
        });
    } else {
        hideClimateCharts();
    }
    document.title = state.page_title;
}

function pageStateFromURL(url)
{
    const url_without_app = url.replace(APP_URL, '');
    const path_parts = url_without_app.split('/');

    if (path_parts.length == 0 || url_without_app == '') {
        return {
            location: null,
            page_title: DEFAULT_PAGE_TITLE,
            lat: null,
            lon: null,
        };
    } else if (path_parts[0] == 'location') {
        if (path_parts.length == 3) {
            return {
                location: null,
                page_title: DEFAULT_PAGE_TITLE,
                lat: parseFloat(decodeURIComponent(path_parts[1])),
                lon: parseFloat(decodeURIComponent(path_parts[2])),
            };
        } else if (path_parts.length == 2) {
            return {
                location: decodeURIComponent(path_parts[1]),
                page_title: 'Climate of ' + decodeURIComponent(path_parts[1]),
                lat: null,
                lon: null,
            };
        } else {
            throw Error('Unexpected URL ' + url);
        }
    } else {
        throw Error('Unexpected URL ' + url);
    }
}
