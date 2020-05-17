/**
 * Unit conversion functions
 *
 * Copyright (c) 2020 Carlos Torchia
 */

import { updateLegend } from './legend.js';

import APP from './app.js';

/**
 * Converts specified data to the specified units ('metric' or 'imperial').
 *
 * Returns cloned data with units updated.
 */
export function convertDataUnits(data, new_units)
{
    let new_data = {};

    for (let key in data) {
        if (Array.isArray(data[key])) {
            new_data[key] = convertToUnits(data[key], new_units);
        } else if (typeof(data[key]) === 'object') {
            new_data[key] = {};

            for (let month in data[key]) {
                new_data[key][month] = convertToUnits(data[key][month], new_units);
            }
        } else {
            new_data[key] = data[key];
        }
    }

    return new_data;
}

/**
 * Converts a value-unit combination to the specified units ('metric' or 'imperial')
 */
export function convertToUnits(datum, new_units)
{
    if (Array.isArray(datum) && datum.length >= 2) {
        let [value, units] = datum;

        switch (new_units) {
            case 'metric':
                break;

            case 'imperial':
                switch (units) {
                    case 'degC':
                        value = value * 9 / 5 + 32;
                        units = 'degF';
                        break;

                    case 'm':
                        value = value * 3.28;
                        units = 'ft';
                        break;

                    case 'mm':
                        value = value / 25.4;
                        units = 'in';
                        break;
                }
                break;

            default:
                throw Error('Unknown units: ' + new_units);
        }

        /* Retain any other elements after the first two. */
        const new_datum = Array.from(datum);

        new_datum[0] = value;
        new_datum[1] = units;

        return new_datum;
    } else {
        throw Error('Expected [value, units, [...]]');
    }
}

/**
 * Returns an English description of the specified units.
 */
export function getUnitLabel(units)
{
    switch (units) {
        case 'degC':
            return '°C';
        case 'degF':
            return '°F';
        case 'mm':
            return 'mm';
        case 'in':
            return 'inches';
        case 'm':
            return 'metres';
        case 'ft':
            return 'feet';
        default:
            throw new Error('Unrecognized units: ' + units);
    }
}

/**
 * Toggles the units from metric to imperial or back.
 */
export function updateUnits()
{
    if (APP.units === 'metric') {
        APP.units = 'imperial';
    } else {
        APP.units = 'metric';
    }

    updateUnitsButton(APP.units);
    window.localStorage.setItem('units', APP.units);
}

/**
 * Updates the units button with the specified units ('metric' or 'imperial').
 */
export function updateUnitsButton(units)
{
    const units_button_text = document.getElementById('units-button-text');

    switch (units) {
        case 'metric':
            units_button_text.innerHTML = '&#176;C';
            break;

        case 'imperial':
            units_button_text.innerHTML = '&#176;F';
            break;

        default:
            throw Error('Invalid units ' + units + ' must be "metric" or "imperial" here.');
    }
}

/**
 * Retrieves the user's preferred units from local storage.
 */
export function fetchPreferredUnits()
{
    return window.localStorage.getItem('units') ? window.localStorage.getItem('units') : 'metric';
}

/**
 * Handles changing the units between "metric" and "imperial".
 */
export function handleUnits()
{
    document.getElementById('units-button').addEventListener('click', function() {
        updateUnits();

        const measurement_select = document.getElementById('measurement');
        updateLegend(measurement_select.value, APP.units);
    });
}
