/**
 * Data sources
 *
 * This module contains functions for working with the
 * list of data sources the user may select.
 *
 * A data source will typically consist of a climate model
 * coupled with a scenario for which that climate model is run.
 *
 * When the user selects a specified data source, we will request
 * data from the API pertaining to that data source, as well as
 * the date range, measurement, and other parameters.
 *
 * Copyright (c) 2020 Carlos Torchia
 */

import { fetchDataSources } from './api.js';

import ssp1_icon from '../images/ssp1.png';
import ssp2_icon from '../images/ssp2.png';
import ssp5_icon from '../images/ssp5.png';

/**
 * Returns the value of the last data source.
 */
export function getLastDataSource(data_source_select)
{
    return data_source_select.getAttribute('data-last');
}

/**
 * Update what was the last data source the user selected.
 */
export function updateLastDataSource(data_source_select)
{
    const selected_data_source = data_source_select.options[data_source_select.selectedIndex].value;
    data_source_select.setAttribute('data-last', selected_data_source);
}

/**
 * Populates the data sources
 */
export async function populateDataSources(data_source_select, date_range_select, measurement_select)
{
    const date_range_option = date_range_select.options[date_range_select.selectedIndex];
    const date_range = date_range_option.value;
    const measurement = measurement_select.value;

    const data_sources = await fetchDataSources(date_range, measurement);

    /* Try to preserve the already selected data source, if any. */
    let selected_data_source;
    if (data_source_select.selectedIndex == -1) {
        selected_data_source = null;
    } else {
        const selected_option = data_source_select.options[data_source_select.selectedIndex];
        selected_data_source = selected_option.value;
    }

    /* Use the last selected data source for this date range, if any. */
    const last_selected_data_source = getLastDataSource(data_source_select);
    let used_previous_data_source = false;

    /* Remove all existing options. */
    data_source_select.innerHTML = '';

    /* Add each data source. */
    for (let i = 0; i <= data_sources.length - 1; i++) {
        let option = document.createElement('option');

        option.text = data_sources[i].name;
        option.value = data_sources[i].code;

        option.setAttribute('data-name', data_sources[i].name);
        option.setAttribute('data-organisation', data_sources[i].organisation);
        option.setAttribute('data-url', data_sources[i].url);
        option.setAttribute('data-max-zoom-level', data_sources[i].max_zoom_level)

        data_source_select.add(option);

        if (option.value === selected_data_source) {
            data_source_select.selectedIndex = i;
            used_previous_data_source = true;
        } else if (option.value === last_selected_data_source) {
            data_source_select.selectedIndex = i;
            used_previous_data_source = true;
        }
    }

    if (!used_previous_data_source) {
        data_source_select.selectedIndex = Math.floor(Math.random() * data_sources.length);
    }
}

/**
 * Gives the attribution for the selected data source.
 */
export function dataSourceAttribution(data_source_select)
{
    const selected_option = data_source_select.options[data_source_select.selectedIndex];
    const data_source_organisation = selected_option.getAttribute('data-organisation');
    const data_source_url = selected_option.getAttribute('data-url');

    return '<a href="' + data_source_url + '">' + data_source_organisation + '</a>';
}

/**
 * Gives the max zoom level for the selected data source.
 */
export function dataSourceMaxZoomLevel(data_source_select)
{
    const selected_option = data_source_select.options[data_source_select.selectedIndex];
    const max_zoom_level = selected_option.getAttribute('data-max-zoom-level');

    return parseInt(max_zoom_level);
}

/**
 * Updates the Shared Socioeconomic Pathway (SSP) button
 * to reflect the currently selected SSP.
 *
 * Right now, the SSP is captured in the data source field.
 * For example, if the selected data source is "CanESM5.ssp245",
 * that means that SSP2 ("middle of the road") is being used.
 */
export function updateSSPButton(data_source)
{
    const [model, ssp] = data_source.split('.ssp');

    if (ssp) {
        showSSPButton();
        const ssp_img = document.getElementById('ssp-img');
        switch (ssp[0]) {
            case '1':
                ssp_img.src = ssp1_icon;
                break;
            case '2':
                ssp_img.src = ssp2_icon;
                break;
            case '5':
                ssp_img.src = ssp5_icon;
                break;
        }
    } else {
        hideSSPButton();
    }
}

/**
 * Shows the SSP button.
 */
function showSSPButton()
{
    const ssp_button = document.getElementById('ssp-button');
    ssp_button.style.display = 'block';

    /* We move the units button, about button and legend down to make room. */
    const units_button = document.getElementById('units-button');
    const about_button = document.getElementById('about-button');
    const legend_div = document.getElementById('legend');

    units_button.style.top = '16.8rem';
    about_button.style.top = '18.9rem';
    legend_div.style.top = '21rem';
}

/**
 * Hides the SSP button.
 */
function hideSSPButton()
{
    const ssp_button = document.getElementById('ssp-button');
    ssp_button.style.display = 'none';

    /* We move the units button, about button and legend back up. */
    const units_button = document.getElementById('units-button');
    const about_button = document.getElementById('about-button');
    const legend_div = document.getElementById('legend');

    units_button.style.top = '14.6rem';
    about_button.style.top = '16.7rem';
    legend_div.style.top = '18.9rem';
}

/**
 * Updates the SSP of the data source when the SSP button is clicked.
 *
 * We toggle the value of SSP, and load the appropriate data source,
 * if it exists.
 *
 * The callback is run if the selected data source is modified to a valid
 * data source.
 */
export function updateSSP(callback)
{
    const data_source_select = document.getElementById('data-source');
    const data_source = data_source_select.value;
    const [selected_model, selected_ssp] = data_source.split('.ssp');

    let ssp_idx = {};

    for (let i = 0; i <= data_source_select.options.length - 1;  i++) {
        const option = data_source_select.options[i];
        const option_model = option.value.split('.', 1)[0];

        if (option_model === selected_model) {
            if (option.value.indexOf('.ssp') !== -1) {
                const option_ssp = option.value.split('.ssp', 2)[1][0];
                ssp_idx[option_ssp] = i;
            }
        }
    }

    const selected_idx = data_source_select.selectedIndex;
    let new_data_source_idx;

    switch (selected_ssp[0]) {
        case '1':
            new_data_source_idx = ssp_idx['2'] !== undefined ? ssp_idx['2'] : (ssp_idx['5'] !== undefined ? ssp_idx['5'] : selected_idx);
            break;
        case '2':
            new_data_source_idx = ssp_idx['5']!== undefined ? ssp_idx['5'] : (ssp_idx['1'] !== undefined ? ssp_idx['1'] : selected_idx);
            break;
        case '5':
            new_data_source_idx = ssp_idx['1']!== undefined ? ssp_idx['1'] : (ssp_idx['2'] !== undefined ? ssp_idx['2'] : selected_idx);
            break;
        default:
            return;
    }

    data_source_select.selectedIndex = new_data_source_idx;

    callback();
}
