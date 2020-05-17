/**
 * Functions having to do with measurements
 * such as temperature and precipitation.
 *
 * Copyright (c) 2020 Carlos Torchia
 */

import { updateLegend } from './legend.js';
import { fireEvent } from './util.js';

import APP from './app.js';

/**
 * Returns an English description of the specified measurement.
 */
export function getMeasurementLabel(measurement)
{
    switch (measurement) {
        case 'precip':
            return 'Precipitation';
        case 'tavg':
            return 'Temperature';
        case 'tmin':
            return 'Minimum Temperature';
        case 'tmax':
            return 'Maximum Temperature';
        case 'et':
            return 'Actual Evapotranspiration';
        case 'potet':
            return 'Potential Evapotranspiration';
        case 'elevation':
            return 'Elevation';
        default:
            throw new Error('Unrecognized measurement: ' + measurement);
    }
}

/**
 * Highlights the correct measurement button.
 */
export function highlightMeasurementButton(measurement)
{
    let selected_button, unselected_buttons;

    switch (measurement) {
        case 'tavg':
            selected_button = document.getElementById('temperature-button');
            unselected_buttons = [
                document.getElementById('precipitation-button'),
                document.getElementById('potet-button'),
            ];
            break;

        case 'precip':
            selected_button = document.getElementById('precipitation-button');
            unselected_buttons = [
                document.getElementById('temperature-button'),
                document.getElementById('potet-button'),
            ];
            break;

        case 'potet':
            selected_button = document.getElementById('potet-button');
            unselected_buttons = [
                document.getElementById('temperature-button'),
                document.getElementById('precipitation-button'),
            ];
            break;

        default:
            throw Error('Unexpected measurement "' + measurement + '"');
    }

    selected_button.classList.add('selected-map-button');

    for (let i = 0; i <= unselected_buttons.length - 1; i++) {
        unselected_buttons[i].classList.remove('selected-map-button');
    }
}

/**
 * Sets the specified drop-down to the specified option
 */
function setDropDown(element_id, desired_option_value)
{
    const select = document.getElementById(element_id);
    const options = select.options;

    for (let i = 0; i <= options.length - 1; i++) {
        if (options[i].value == desired_option_value) {
            select.selectedIndex = i;
            fireEvent(select, 'change');
            return;
        }
    }
}

/**
 * Handles changes to the measurement controls.
 */
export function handleMeasurementChanges()
{
    document.getElementById('measurement').addEventListener('change', function() {
        highlightMeasurementButton(this.value);
        updateLegend(this.value, APP.units);
    });

    document.getElementById('temperature-button').onclick = function() {
        setDropDown('measurement', 'tavg');
    };

    document.getElementById('precipitation-button').onclick = function() {
        setDropDown('measurement', 'precip');
    };

    document.getElementById('potet-button').onclick = function() {
        setDropDown('measurement', 'potet');
    };
}
