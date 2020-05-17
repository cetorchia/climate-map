/**
 * Makes requests to the API on behalf of the JavaScript UI.
 *
 * Copyright (c) 2020 Carlos Torchia
 */

import { showError, hideError } from './error.js';

export const API_URL = '/api';

const NOT_FOUND_ERROR_MESSAGE = 'Could not find the specified resource.';
const API_ERROR_MESSAGE = 'An error occurred while fetching from the API.';
const SEARCH_NOT_FOUND = 'Could not find the specified location.';
const LOCATION_NOT_FOUND = 'Data at the specified location is unavailable.';
const PLACES_ERROR = 'Could not retrieve places and all their climates.';

/**
 * Makes a request to the API.
 */
async function fetchFromAPI(url)
{
    const response = await fetch(url).then((response) => {
        // Credit: https://stackoverflow.com/a/54164027
        if (response.status >= 400 && response.status < 600) {
            if (response.status == 404) {
                throw new Error(NOT_FOUND_ERROR_MESSAGE);
            } else {
                throw new Error(API_ERROR_MESSAGE);
            }
        }

        return response;
    });
    return response.json();
}

/**
 * Gives a promise to the list of all datasets for the specified
 * data source.
 */
export async function fetchDateRanges()
{
    const url = API_URL + '/date-ranges';

    try {
        return await fetchFromAPI(url);
    } catch(err) {
        showError();
        throw err;
    }
}

/**
 * Gives a promise to the list of data sources that have
 * datasets in the specified date range and measurement.
 */
export async function fetchDataSources(date_range, measurement)
{
    const url = API_URL + '/data-sources/' + encodeURIComponent(date_range) + '/' + encodeURIComponent(measurement);

    try {
        return await fetchFromAPI(url);
    } catch(err) {
        showError();
        throw err;
    }
}

/**
 * Fetches the places with climate normals indexed by
 * latitude and longitude.
 */
export async function fetchClimatesOfPlaces(data_source, date_range, measurement, period, bounds)
{
    const min_lat = bounds.getSouth();
    const max_lat = bounds.getNorth();
    const min_lon = bounds.getWest();
    const max_lon = bounds.getEast();

    const url =
        API_URL + '/places/' +
        encodeURIComponent(data_source) + '/' +
        encodeURIComponent(date_range) + '/' +
        encodeURIComponent(measurement) + '-' + encodeURIComponent(period) +
        '?' +
        'min_lat=' + encodeURIComponent(min_lat) + '&' +
        'max_lat=' + encodeURIComponent(max_lat) + '&' +
        'min_lon=' + encodeURIComponent(min_lon) + '&' +
        'max_lon=' + encodeURIComponent(max_lon);

    try {
        return await fetchFromAPI(url);
    } catch(err) {
        showError(PLACES_ERROR);
        throw err;
    }
}

/**
 * Maps a coordinate to the range -180 to 180.
 */
function mapCoordinateWithin180(coord)
{
    if (coord >= -180) {
        return (coord + 180) % 360 - 180;
    } else {
        return (coord + 180) % 360 + 180;
    }
}

/**
 * Returns the URL for the specified climate data by latitude and longitude.
 */
function climateDataUrlForCoords(data_source, date_range, lat, lon)
{
    /* Wrap around to allow the user to scroll past the whole map multiple times */
    lat = mapCoordinateWithin180(lat);
    lon = mapCoordinateWithin180(lon);

    return API_URL + '/monthly-normals/' + data_source + '/' + date_range + '/' + lat + '/' + lon;
}

/**
 * Fetches data for the specified coordinates and date range.
 */
export async function fetchClimateDataForCoords(data_source, date_range, lat, lon)
{
    const url = climateDataUrlForCoords(data_source, date_range, lat, lon);
    let data;

    try {
        data = await fetchFromAPI(url);
        hideError();
    } catch(err) {
        if (err.message == NOT_FOUND_ERROR_MESSAGE) {
            showError(LOCATION_NOT_FOUND);
        } else {
            showError();
        }
        throw err;
    }

    data = populateMissingTemperatureData(data);

    if (data['tavg'] !== undefined) {
        if (data['tavg'][0] === undefined) {
            data['tavg'][0] = getAverageTemperature(data['tavg']);
        }
    }

    if (data['precip'] !== undefined) {
        if (data['precip'][0] === undefined) {
            data['precip'][0] = getTotalPrecipitation(data['precip']);
        }
    }

    if (data['potet'] !== undefined) {
        if (data['potet'][0] === undefined) {
            data['potet'][0] = getTotalPrecipitation(data['potet']);
        }
    }

    return data;
}

/**
 * Populates missing mean, minimum, or maximum data.
 * This allows us to not have to store all data which will save
 * us time.
 */
function populateMissingTemperatureData(data)
{
    if (data['tavg'] === undefined) {
        data['tavg'] = {};
    }

    if (data['tmin'] === undefined) {
        data['tmin'] = {};
    }

    if (data['tmax'] === undefined) {
        data['tmax'] = {};
    }

    for (let month = 1; month <= 12; month++) {
        let tavg = data['tavg'][month] !== undefined ? data['tavg'][month][0] : null;
        let tmin = data['tmin'][month] !== undefined ? data['tmin'][month][0] : null;
        let tmax = data['tmax'][month] !== undefined ? data['tmax'][month][0] : null;

        if (tavg === null && tmin !== null && tmax !== null) {
            let units = data['tmin'][month][1];
            data['tavg'][month] = [
                Math.round((tmin + tmax) / 2 * 10) / 10,
                units,
            ];
        }

        if (tmin === null && tavg !== null && tmax !== null) {
            let units = data['tavg'][month][1];
            data['tmin'][month] = [
                Math.round((2 * tavg - tmax) * 10) / 10,
                units,
            ];
        }

        if (tmax === null && tavg !== null && tmin !== null) {
            let units = data['tavg'][month][1];
            data['tmax'][month] = [
                Math.round((2 * tavg - tmin) * 10) / 10,
                units,
            ];
        }
    }

    return data;
}

/**
 * Returns the average of all the temperatures in the specified object.
 *
 * @return Array [average, units]
 */
function getAverageTemperature(temperatures)
{
    let sum = 0;
    let num = 0;
    let units = undefined;

    for (let month = 1; month <= 12; month++) {
        if (temperatures[month] !== undefined) {
            sum += temperatures[month][0];
            units = temperatures[month][1];
            num++;
        } else {
            console.warn('Missing month ' + month + ' in temperature');
        }
    }

    let average = num > 0 ? sum / num : undefined;
    return [average, units];
}

/**
 * Returns the total of all the precipitations in the specified object.
 *
 * @return Array [total, units]
 */
function getTotalPrecipitation(precipitations)
{
    let sum = 0;
    let num = 0;
    let units = undefined;

    for (let month = 1; month <= 12; month++) {
        if (precipitations[month] !== undefined) {
            sum += precipitations[month][0];
            units = precipitations[month][1];
            num++;
        } else {
            console.warn('Missing month ' + month + ' in precipitation');
        }
    }

    let total = num > 0 ? sum : undefined;
    return [total, units];
}

/**
 * Does a search using the API.
 */
export async function search(query)
{
    const url = API_URL + '/search/' + encodeURIComponent(query);

    try {
        const geoname = await fetchFromAPI(url);
        hideError();
        return geoname;
    } catch(err) {
        if (err.message == NOT_FOUND_ERROR_MESSAGE) {
            showError(SEARCH_NOT_FOUND);
        } else {
            showError();
        }
        throw err;
    }
}
