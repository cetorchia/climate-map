/**
 * Main climate map javascript.
 *
 * Copyright (c) 2020 Carlos Torchia
 */

import CONFIG from '../config/config.json';
import './style.css';

let L, Chart;

async function importDependencies()
{
    try {
        const {default: L} = await import(/* webpackChunkName: "leaflet" */ 'leaflet/dist/leaflet-src.js');
        const {default: Chart} = await import(/* webpackChunkName: "chartjs" */ 'chart.js/dist/Chart.bundle.js');

        await import('leaflet/dist/leaflet.css');
        await import(/* webpackChunkName: "mapbox-gl-leaflet" */ 'mapbox-gl-leaflet');
        await import('mapbox-gl/dist/mapbox-gl.css');

        // Hack so that leaflet's images work after going through webpack
        // @see https://github.com/PaulLeCam/react-leaflet/issues/255#issuecomment-388492108
        const {default: marker} = await import('leaflet/dist/images/marker-icon.png');
        const {default: marker2x} = await import('leaflet/dist/images/marker-icon-2x.png');
        const {default: markerShadow} = await import('leaflet/dist/images/marker-shadow.png');

        delete L.Icon.Default.prototype._getIconUrl;

        L.Icon.Default.mergeOptions({
            iconRetinaUrl: marker2x,
            iconUrl: marker,
            shadowUrl: markerShadow
        });

        return [L, Chart];
    } catch (err) {
        showError('An error occurred fetching dependencies. Please try again later.');
        console.error(err);
        throw err;
    }
}

/**
 * Climate data resolution. Offset is used in case each data point does not
 * start at some multiple of the delta.
 */
const DELTA = 1/24, DELTA_OFFSET = 0;

/**
 * Default error message.
 */
const DEFAULT_ERROR_MESSAGE = 'An error occurred. Please try again later.';
const NOT_FOUND_ERROR_MESSAGE = 'Could not find the specified resource.';
const API_ERROR_MESSAGE = 'An error occurred while fetching from the API.';
const SEARCH_NOT_FOUND = 'Could not find the specified location.';
const LOCATION_NOT_FOUND = 'Data at the specified location is unavailable.';
const TILE_ERROR_MESSAGE = 'Could not fetch climate map overlay. Please try again later.';

const DEFAULT_PAGE_TITLE = 'Climate Map';

const API_URL = '/api';
const APP_URL = '/';

let APP = {};

let defaultDataSources = {};

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
 * Does a search using the API.
 */
async function search(query)
{
    const url = API_URL + '/search/' + encodeURIComponent(query);

    try {
        const data = await fetchFromAPI(url);
        hideError();
        return data;
    } catch(err) {
        if (err.message == NOT_FOUND_ERROR_MESSAGE) {
            showError(SEARCH_NOT_FOUND);
        } else {
            showError();
        }
        throw err;
    }
}

/**
 * Gives a promise to the list of all datasets for the specified
 * data source.
 */
async function fetchDateRanges()
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
 * Gives a promise to the list of all active data sources.
 */
async function fetchDataSources(date_range)
{
    const url = API_URL + '/data-sources/' + encodeURIComponent(date_range);

    try {
        return await fetchFromAPI(url);
    } catch(err) {
        showError();
        throw err;
    }
}

/**
 * Returns the URL for the specified climate data.
 */
function tileUrl(data_source, date_range, measurement, period)
{
    return CONFIG.climate_tile_layer.url + '/' +
        encodeURIComponent(data_source) + '/' +
        encodeURIComponent(date_range) + '/' +
        encodeURIComponent(measurement + '-' + period) +
        '/{z}/{x}/{y}.jpeg';
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
async function fetchClimateDataForCoords(data_source, date_range, lat, lon)
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

    if (data['tavg'][0] === undefined) {
        data['tavg'][0] = getAverageTemperature(data['tavg']);
    }

    if (data['tmin'][0] === undefined) {
        data['tmin'][0] = getAverageTemperature(data['tmin']);
    }

    if (data['tmax'][0] === undefined) {
        data['tmax'][0] = getAverageTemperature(data['tmax']);
    }

    if (data['precip'][0] === undefined) {
        data['precip'][0] = getTotalPrecipitation(data['precip']);
    }

    return data;
}

/**
 * Updates the tile layer for the climate filters in the document.
 */
function updateTileLayer(tile_layer)
{
    const data_source_select = document.getElementById('data-source');
    const date_range_select = document.getElementById('date-range');
    const measurement_select = document.getElementById('measurement');
    const period_select = document.getElementById('period');

    const data_source = data_source_select.value;
    const date_range = date_range_select.value;
    const measurement = measurement_select.value;
    const period = period_select.value;

    tile_layer.setUrl(
        tileUrl(data_source, date_range, measurement, period, 'tiles')
    );
    tile_layer.options.maxNativeZoom = dataSourceMaxZoomLevel(data_source_select);
}

/**
 * Creates an tile layer with climate data based on the inputs.
 * This shows the differences between different regions' climates in a visual way.
 *
 * @return map layer
 */
function createTileLayer()
{
    const data_source_select = document.getElementById('data-source');
    const date_range_select = document.getElementById('date-range');
    const measurement_select = document.getElementById('measurement');
    const period_select = document.getElementById('period');

    const data_source = data_source_select.value;
    const date_range = date_range_select.value;
    const measurement = measurement_select.value;
    const period = period_select.value;

    const max_zoom_level = dataSourceMaxZoomLevel(data_source_select);
    const tile_layer = L.tileLayer(
        tileUrl(data_source, date_range, measurement, period, 'tiles'),
        {
            attribution: dataSourceAttribution(data_source_select),
            zIndex: CONFIG.climate_tile_layer.z_index,
            maxNativeZoom: max_zoom_level,
            opacity: CONFIG.climate_tile_layer.opacity,
            bounds: [[85.051129, -180], [-85.051129 + DELTA/2, 180 - DELTA/2]],
        }
    );

    tile_layer.on('tileerror', function() {
        showError(TILE_ERROR_MESSAGE);
    });

    return tile_layer;
}

/**
 * Returns the colour for the specified value with units.
 */
function colourForValueAndUnits(value, units)
{
    let red, green, blue;

    switch (units) {
        case 'degC':

            if (value >= 40) {
                red = 255;
                green = 0;
                blue = 0;
            } else if (value >= 0) {
                red = 255;
                green = 240 - 6 * value;
                blue = green;
            } else if (value <= -40) {
                red = 0;
                green = 0;
                blue = 255;
            } else {
                red = 240 + 6 * value;
                green = red;
                blue = 255;
            }

            return 'rgb(' + red + ',' + green + ',' + blue + ')';

        case 'mm':
            if (value >= 100) {
                red = 0;
                green = 255;
                blue = 0;
            } else if (value >= 50) {
                red = 240 - 4.7 * (value - 50);
                green = 255;
                blue = red;
            } else {
                red = 230 - value / 3;
                green = 230;
                blue = 4.4 * value;
            }

            return 'rgb(' + red + ',' + green + ',' + blue + ')';

        default:
            return '#22b';
    }
}

/**
 * Returns the colours for each month based on the value
 * and units. This gives a visual sense of the temperature
 * or precipitation amount.
 */
function coloursForMonthData(values, units)
{
    let colours = [];

    for (let i = 0; i <= values.length - 1; i++) {
        const value = values[i];
        const colour = colourForValueAndUnits(value, units);
        colours.push(colour);
    }

    return colours;
}

/**
 * Shows a climate chart with the specified data.
 * The datasets must all have the same units.
 *
 * @return Chart
 */
function createClimateChart(datasets, units, labels, type, canvas_id)
{
    const ctx = document.getElementById(canvas_id).getContext('2d');

    /* Collect temperature means for each month in a linear fashion. */
    let chart_datasets = [];

    if (type == 'bar' && datasets.length == 3 && units == 'degC') {
        /**
         * Assume datasets are the mean, min, and max temperatures. Create a floating bar
         * chart with the bottom of the bars being minimum and the top being maximum.
         */
        let values = [];
        let mean_values = [];
        const mean_data = datasets[0];
        const min_data = datasets[1];
        const max_data = datasets[2];
        const label = labels[1] + ' and ' + labels[2];

        for (let month = 1; month <= 12; month++) {
            let min_value, max_value;

            if (mean_data[month] !== undefined) {
                if (mean_data[month][1] !== units) {
                    throw new Error('Expected ' + units + ', got ' + mean_data[month][1]);
                }
                mean_values.push(mean_data[month][0]);
            } else {
                mean_values.push(null);

                console.error('Missing month ' + month + ' in ' + labels[0]);
            }

            if (min_data[month] !== undefined) {
                if (min_data[month][1] !== units) {
                    throw new Error('Expected ' + units + ', got ' + min_data[month][1]);
                }
                min_value = min_data[month][0];
            } else {
                min_value = null;

                console.error('Missing month ' + month + ' in ' + labels[1]);
            }

            if (max_data[month] !== undefined) {
                if (max_data[month][1] !== units) {
                    throw new Error('Expected ' + units + ', got ' + max_data[month][1]);
                }
                max_value = max_data[month][0];
            } else {
                max_value = null;

                console.error('Missing month ' + month + ' in ' + labels[2]);
            }

            values.push([min_value, max_value]);
        }

        const colours = coloursForMonthData(mean_values, units);
        chart_datasets.push(
            {
                label: labels[0],
                data: mean_values,
                backgroundColor: '#000',
                type: 'scatter',
            },
            {
                label: label,
                data: values,
                backgroundColor: colours,
                hoverBackgroundColor: '#555',
            }
        );
    } else {
        /**
         * Put each dataset as separate charts on the same axes.
         */
        for (let i = 0; i <= datasets.length - 1; i++) {
            let values = [];
            const data = datasets[i];
            const label = labels[i];

            for (let month = 1; month <= 12; month++) {
                if (data[month] !== undefined) {
                    if (data[month][1] !== units) {
                        throw new Error('Expected ' + units + ', got ' + data[month][1]);
                    }
                    values.push(data[month][0]);
                } else {
                    /* If data is undefined put fake data for now. */
                    values.push(null);

                    console.warn('Missing month ' + month + ' in ' + label);
                }
            }

            const colours = coloursForMonthData(values, units);
            const avg_colour = colourForValueAndUnits(data[0][0], data[0][1]);

            if (type == 'line') {
                /**
                 * Do an area line chart.
                 * Chart.js will not do a multi-coloured area chart, otherwise
                 * we could have a gradient to show the change.
                 */
                chart_datasets.push(
                    {
                        label: label,
                        data: values,
                        backgroundColor: avg_colour,
                        borderColor: avg_colour,
                        fill: 0,
                        cubicInterpolationMode: 'monotone',
                    }
                );
            } else {
                chart_datasets.push(
                    {
                        label: label,
                        data: values,
                        backgroundColor: colours,
                    }
                );
            }
        }
    }

    /* Create the chart. */
    //const stacked = (type == 'line' && datasets.length > 1);
    const chart = new Chart(ctx, {
        type: type,
        data: {
            labels: [
                'January',
                'February',
                'March',
                'April',
                'May',
                'June',
                'July',
                'August',
                'September',
                'October',
                'November',
                'December',
            ],
            datasets: chart_datasets,
        },
        options: {
            scales: {
                yAxes: [{
                    ticks: {
                        beginAtZero: true
                    },
                    //stacked: stacked,
                }]
            }
        },
    });

    return chart;
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
 * Updates the climate chart.
 */
function updateClimateChart(data)
{
    const average_temperature = Math.round(data['tavg'][0][0] * 10) / 10;
    const total_precipitation = Math.round(data['precip'][0][0] * 10) / 10;

    document.getElementById('average-temperature').textContent = average_temperature;
    document.getElementById('total-precipitation').textContent = total_precipitation;

    if (APP.temp_chart !== undefined) {
        APP.temp_chart.destroy();
    }

    APP.temp_chart = createClimateChart(
        [
            data['tavg'],
            ('tmin' in data ? data['tmin'] : {}),
            ('tmax' in data ? data['tmax'] : {}),
        ],
        'degC',
        [
            'Mean Temperature (°C)',
            'Min Temperature (°C)',
            'Max Temperature (°C)',
        ],
        'bar',
        'location-temperature-chart'
    );

    if (APP.precip_chart !== undefined) {
        APP.precip_chart.destroy();
    }
    APP.precip_chart = createClimateChart(
        [data['precip']],
        'mm',
        ['Precipitation (mm)'],
        'bar',
        'location-precipitation-chart'
    );
}

/**
 * Handle changes to the filters. We will update the map's colours.
 */
function updateTilesAndChart()
{
    updateTileLayer(APP.climate_tile_layer);

    if (APP.clicked_lat && APP.clicked_lon) {
        const data_source_select = document.getElementById('data-source');
        const date_range_select = document.getElementById('date-range');
        const data_source = data_source_select.value;
        const date_range = date_range_select.value;

        fetchClimateDataForCoords(data_source, date_range, APP.clicked_lat, APP.clicked_lon).then(
            updateClimateChart);
    }
}


/**
 * Highlights the correct measurement button.
 */
function highlightMeasurementButton(measurement)
{
    let selected_button, unselected_buttons;

    switch (measurement) {
        case 'tavg':
            selected_button = document.getElementById('temperature-button');
            unselected_buttons = [
                document.getElementById('precipitation-button'),
            ];
            break;

        case 'precip':
            selected_button = document.getElementById('precipitation-button');
            unselected_buttons = [
                document.getElementById('temperature-button'),
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
 * Update the legend for the specified measurement.
 */
function updateLegend(measurement)
{
    const legend_img = document.getElementById('legend-img');

    if (['tavg', 'tmin', 'tmax'].indexOf(measurement) !== -1) {
        legend_img.src = '/legend-temp.png';
    } else if (measurement == 'precip') {
        legend_img.src = '/legend-precip.png';
    }
}

/**
 * Returns the value of the last data source.
 */
function getLastDataSource(data_source_select)
{
    return data_source_select.getAttribute('data-last');
}

/**
 * Update what was the last data source the user selected.
 */
function updateLastDataSource(data_source_select)
{
    const selected_data_source = data_source_select.options[data_source_select.selectedIndex].value;
    data_source_select.setAttribute('data-last', selected_data_source);
}

/**
 * Populates the data sources
 */
async function populateDataSources(data_source_select, date_range_select)
{
    const date_range_option = date_range_select.options[date_range_select.selectedIndex];
    const date_range = date_range_option.value;

    const data_sources = await fetchDataSources(date_range);

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
 * Populates the date ranges from valid datasets for this data source.
 */
async function populateDateRanges(date_range_select)
{
    const date_ranges = await fetchDateRanges();

    /* Remove all existing options. */
    date_range_select.innerHTML = '';

    /* Add each data source. */
    for (let i = 0; i <= date_ranges.length - 1; i++) {
        let date_range = date_ranges[i];
        let option = document.createElement('option');

        option.text = date_range;
        option.value = date_range;

        date_range_select.add(option);
    }

    populateDateRangeSlider(date_ranges, date_range_select.selectedIndex);
}

/**
 * Populates the data list for the date range slider.
 */
function populateDateRangeSlider(date_ranges, selected_index)
{
    const date_range_slider = document.getElementById('date-range-slider');

    date_range_slider.min = 0;
    date_range_slider.max = date_ranges.length - 1;
    date_range_slider.value = selected_index;
}

/**
 * Updates the tooltip below the date range slider to show
 * the selected date range.
 */
function updateDateRangeSliderTooltip()
{
    const selected_index = document.getElementById('date-range-slider').value;
    const date_range = document.getElementById('date-range').options[selected_index].value;
    const tooltip = document.getElementById('date-range-slider-tooltip');
    tooltip.style.display = 'block';
    tooltip.innerHTML = date_range;
}

/**
 * Hides the tooltip below the date range
 */
function hideDateRangeSliderTooltip()
{
    const tooltip = document.getElementById('date-range-slider-tooltip');
    tooltip.style.display = 'none';
}

/**
 * Returns an English description of the specified measurement.
 */
function getMeasurementLabel(measurement)
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
        default:
            throw new Error('Unrecognized measurement: ' + measurement);
    }
}

/**
 * Returns an English description of the specified period.
 */
function getPeriodLabel(period)
{
    switch (period) {
        case 'year':
            return 'Year-round';
        case '12_01_02':
            return 'Dec-Feb';
        case '03_04_05':
            return 'Mar-May';
        case '06_07_08':
            return 'Jun-Aug';
        case '09_10_11':
            return 'Sep-Nov';
        default:
            throw new Error('Unrecognized period: ' + period);
    }
}

/**
 * Updates the description tooltip to give the user
 * an idea about what they're seeing.
 */
function updateDescriptionTooltip(period, measurement, date_range)
{
    const tooltip = document.getElementById('description-tooltip');
    const period_label = getPeriodLabel(period);
    const measurement_label = getMeasurementLabel(measurement);
    const text = 'Average ' + period_label + ' ' + measurement_label + ', ' + date_range;

    tooltip.textContent = text;
}

/**
 * Gives the attribution for the selected data source.
 */
function dataSourceAttribution(data_source_select)
{
    const selected_option = data_source_select.options[data_source_select.selectedIndex];
    const data_source_organisation = selected_option.getAttribute('data-organisation');
    const data_source_url = selected_option.getAttribute('data-url');

    return 'Climate data &copy; <a href="' + data_source_url + '">' + data_source_organisation + '</a>';
}

/**
 * Gives the max zoom level for the selected data source.
 */
function dataSourceMaxZoomLevel(data_source_select)
{
    const selected_option = data_source_select.options[data_source_select.selectedIndex];
    const max_zoom_level = selected_option.getAttribute('data-max-zoom-level');

    return parseInt(max_zoom_level);
}

/**
 * Handle clicks on the climate map. We will show a bunch of information
 * about that particular location's climate.
 */
function loadLocationClimate(lat, lon, location_title)
{
    const data_source_select = document.getElementById('data-source');
    const date_range_select = document.getElementById('date-range');
    const data_source = data_source_select.value;
    const date_range = date_range_select.value;

    return fetchClimateDataForCoords(data_source, date_range, lat, lon).then(function(data) {
        APP.location_marker.setLatLng([lat, lon]).addTo(APP.climate_map).on('click', function() {
            showLocationTitle(location_title);
            showLocationClimate();
            updatePageState(lat, lon, location_title);
        });

        updateClimateChart(data);
        showLocationTitle(location_title);
        showLocationClimate();

        APP.clicked_lat = lat;
        APP.clicked_lon = lon;

        return [lat, lon, location_title];
    });
}

/**
 * Shows the location climate container.
 */
function showLocationClimate()
{
    document.getElementById('location-climate').style.display = 'block';
}

/**
 * Hides the location climate container.
 */
function hideLocationClimate()
{
    document.getElementById('location-climate').style.display = 'none';
}

/**
 * Searches for the location specified in the search box
 * and shows the climate of the location.
 */
async function doSearch(search_query) {
    const data = await search(search_query);
    const lat = data['latitude'];
    const lon = data['longitude'];

    document.getElementById('search-container').style.display = 'none';

    APP.climate_map.setView([lat, lon], CONFIG.max_zoom);

    let place_name = data['name'];

    if (data['province']) {
        place_name += ', ' + data['province'];
    } else if (data['country']) {
        place_name += ', ' + data['country'];
    }

    return [lat, lon, place_name];
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
            return;
        }
    }
}

/**
 * Displays an error message on the screen.
 */
function showError(message)
{
    if (message === undefined) {
        message = DEFAULT_ERROR_MESSAGE;
    }

    let error_container = document.getElementById('error-container');

    if (error_container) {
        error_container.style.display = 'block';
        const message_span = document.getElementById('error-span');
        message_span.textContent = escapeHtmlTags(message);
    } else {
        error_container = document.createElement('div');
        error_container.setAttribute('id', 'error-container');
        error_container.setAttribute('class', 'map-window');

        const message_span = document.createElement('span');
        message_span.setAttribute('id', 'error-span');
        message_span.textContent = escapeHtmlTags(message);
        error_container.append(message_span);

        const error_close = document.createElement('div');
        error_close.setAttribute('id', 'error-container-close');
        error_close.setAttribute('class', 'container-close');
        error_close.textContent = 'X';
        error_close.onclick = hideError;
        error_container.append(error_close);

        const body = document.getElementsByTagName('body')[0];
        body.append(error_container);
    }

    return error_container;
}

/**
 * Hides the error message.
 */
function hideError()
{
    const error_container = document.getElementById('error-container');

    if (error_container !== null) {
        error_container.style.display = 'none';
    }
}

/**
 * Strips tags from input.
 * See https://stackoverflow.com/a/5499821
 */
function escapeHtmlTags(str)
{
    const tags_to_replace = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
    };

    function replace_tag(tag) {
        return tags_to_replace[tag] || tag;
    }

    return str.replace(/[&<>]/g, replace_tag);
}

function showLocationTitle(location_title)
{
    const location_title_span = document.getElementById('location-title');

    if (location_title) {
        location_title_span.innerHTML = location_title + ' <a href="">&#128279;</a>';
        location_title_span.style.display = 'block';
    } else {
        location_title_span.style.display = 'none';
    }
}

/**
 * Updates the state of the page. This will update the
 * URL given the current "location" in the app.
 */
function updatePageState(lat, lon, location, page_title)
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
function goToURL(url)
{
    const state = pageStateFromURL(url);
    goToPageState(state);
    window.history.replaceState(state, state.page_title);
}

function goToPageState(state)
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
        hideLocationClimate();
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

/**
 * Returns the email address of the specified contact.
 */
function getContact(contact_name)
{
    return CONFIG.contact[contact_name].username + '@' + CONFIG.contact[contact_name].domain;
}

/**
 * Loads the climate map.
 */
window.onload = async function() {
    [L, Chart] = await importDependencies();

    /**
     * Create the leaflet map.
     */
    APP.climate_map = L.map('climate-map').setView([0, 0], CONFIG.min_zoom);

    if (CONFIG.min_zoom !== undefined) {
        APP.climate_map.options.minZoom = CONFIG.min_zoom;
    }

    if (CONFIG.max_zoom !== undefined) {
        APP.climate_map.options.maxZoom = CONFIG.max_zoom;
    }

    /**
     * Show the basemaps defined in the config file.
     */
    for (let i = 0; i <= CONFIG.tile_layers.length - 1; i++) {
        const tile_layer = CONFIG.tile_layers[i];

        if (tile_layer.mapboxGL) {
            L.mapboxGL({
                attribution: tile_layer.attribution,
                accessToken: tile_layer.access_token,
                style: tile_layer.style_url,
                zIndex: tile_layer.z_index,
            }).addTo(APP.climate_map);
        } else {
            L.tileLayer(tile_layer.url, {
                attribution: tile_layer.attribution,
                zIndex: tile_layer.z_index,
            }).addTo(APP.climate_map);
        }
    }

    APP.location_marker = L.marker([0, 0]);

    const data_source_select = document.getElementById('data-source');
    const date_range_select = document.getElementById('date-range');
    const measurement_select = document.getElementById('measurement');
    const period_select = document.getElementById('period');
    const search_input = document.getElementById('search');

    /**
     * Populate the drop downs and render the climate map tiles.
     * Also show the location climate if there is a location in the
     * URL path.
     */
    populateDateRanges(date_range_select).then(function() {
        populateDataSources(data_source_select, date_range_select).then(function() {
            APP.climate_tile_layer = createTileLayer().addTo(APP.climate_map);
            highlightMeasurementButton(measurement_select.value);
            updateDescriptionTooltip(period_select.value, measurement_select.value, date_range_select.value);
            updateLegend(measurement_select.value);
            goToURL(document.location.pathname); 
        });
    });

    /**
     * Handle changing the data source
     */
    function change_data_source() {
        updateTilesAndChart();

        APP.climate_tile_layer.remove();
        APP.climate_tile_layer.options.attribution = dataSourceAttribution(data_source_select);
        APP.climate_tile_layer.addTo(APP.climate_map);
    }

    data_source_select.onchange = function() {
        change_data_source();
        updateLastDataSource(data_source_select);
    };

    /**
     * Handle changing the date range dropdown.
     */
    function change_date_range() {
        populateDataSources(data_source_select, date_range_select).then(change_data_source).then(function() {
            if (!getLastDataSource(data_source_select)) {
                updateLastDataSource(data_source_select);
            }
        });
        updateDescriptionTooltip(period_select.value, measurement_select.value, date_range_select.value);
    }

    date_range_select.onchange = function() {
        change_date_range();
        document.getElementById('date-range-slider').value = date_range_select.selectedIndex;
    };

    /**
     * Handle sliding the date range slider.
     */
    const date_range_slider = document.getElementById('date-range-slider');

    date_range_slider.onchange = function(e) {
        date_range_select.selectedIndex = e.target.value;
        change_date_range();
        hideDateRangeSliderTooltip();
    };

    date_range_slider.onmousedown = updateDateRangeSliderTooltip;
    date_range_slider.onmouseup = hideDateRangeSliderTooltip;
    date_range_slider.oninput = updateDateRangeSliderTooltip;
    date_range_slider.onkeydown = updateDateRangeSliderTooltip;

    /**
     * Handle changing the measurement dropdown
     */
    function change_measurement() {
        updateTileLayer(APP.climate_tile_layer);
        highlightMeasurementButton(measurement_select.value);
        updateLegend(measurement_select.value);
        updateDescriptionTooltip(period_select.value, measurement_select.value, date_range_select.value);
    }

    measurement_select.onchange = change_measurement;

    /**
     * Handle changing the period dropdown.
     */
    period_select.onchange = function() {
        updateTileLayer(APP.climate_tile_layer);
        updateDescriptionTooltip(period_select.value, measurement_select.value, date_range_select.value);
    };

    /**
     * Handle clicking at a location on the map.
     */
    APP.climate_map.on('click', function(e) {
        const lat = e.latlng.lat;
        const lon = e.latlng.lng;

        loadLocationClimate(lat, lon).then(function() {
            updatePageState(lat, lon);
        });
    });

    document.getElementById('close-location-climate').onclick = function() {
        hideLocationClimate();
        updatePageState();
    };

    /**
     * Handle search.
     */
    function do_search(search_query) {
        if (search_query) {
            doSearch(search_query).then(([lat, lon, display_name]) => {
                loadLocationClimate(lat, lon, display_name).then(([lat, lon, display_name]) => {
                    updatePageState(lat, lon, display_name);
                });
            });
        }
    }

    document.getElementById('search-button').onclick = function() {
        do_search(search_input.value);
    }

    search_input.addEventListener('keyup', function(event) {
        /* Credit: https://www.w3schools.com/howto/howto_js_trigger_button_enter.asp */
        event.preventDefault();
        if (event.keyCode === 13) {
            do_search(search_input.value);
        }
    });

    /**
     * Handle clicking the buttons on the side.
     */
    document.getElementById('filter-button').onclick = function() {
        this.classList.toggle('hamburger-close');
        const filters_div = document.getElementById('filter-container');
        filters_div.style.display = (filters_div.style.display == 'none') ? 'block' : 'none';
    };

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

    document.getElementById('temperature-button').onclick = function() {
        setDropDown('measurement', 'tavg');
        change_measurement();
    };

    document.getElementById('precipitation-button').onclick = function() {
        setDropDown('measurement', 'precip');
        change_measurement();
    };

    document.getElementById('about-button').onclick = function() {
        const about_div = document.getElementById('about');
        about_div.style.display = (about_div.style.display == 'none') ? 'block' : 'none';
    };

    document.getElementById('close-about').onclick = function() {
        const about_div = document.getElementById('about');
        about_div.style.display = 'none';
    };

    /**
     * Handle the back button.
     */
    window.onpopstate = function(e) {
        if (e.state) {
            goToPageState(e.state);
        }
    };

    /**
     * Display the support contact.
     */
    const support_contact = getContact('support');
    document.getElementById('support-contact').innerHTML =
        '<a href="mailto:' + support_contact + '">' + support_contact + '</a>';
};
