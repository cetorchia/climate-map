/**
 * Main climate map javascript.
 *
 * Copyright (c) 2020 Carlos Torchia
 */

import L from 'leaflet';
import Chart from 'chart.js';
import './style.css';
import 'leaflet/dist/leaflet.css';

// Hack so that leaflet's images work after going through webpack
// @ see https://github.com/PaulLeCam/react-leaflet/issues/255#issuecomment-388492108
import marker from 'leaflet/dist/images/marker-icon.png';
import marker2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

delete L.Icon.Default.prototype._getIconUrl;

L.Icon.Default.mergeOptions({
    iconRetinaUrl: marker2x,
    iconUrl: marker,
    shadowUrl: markerShadow
});

/**
 * Climate data resolution. Offset is used in case each data point does not
 * start at some multiple of the delta.
 */
const DELTA = 1/12, DELTA_OFFSET = 0;

/**
 * Does a search using the API.
 */
async function search(query)
{
    const url = 'api/search/' + encodeURIComponent(query);

    const response = await fetch(url);

    return response.json();
}

/**
 * Gives a promise to the list of all datasets for the specified
 * data source.
 */
async function fetchDateRanges()
{
    const url = 'api/date-ranges';

    const response = await fetch(url);

    return response.json();
}

/**
 * Gives a promise to the list of all active data sources.
 */
async function fetchDataSources(date_range)
{
    const url = 'api/data-sources/' + date_range;

    const response = await fetch(url);

    return response.json();
}

/**
 * Returns the URL for the specified climate data.
 */
function climateDataUrl(data_source, date_range, measurement, month, fmt)
{
    if (fmt == 'tiles') {
        if (month) {
            return 'data/' + data_source + '/' + date_range + '/' + fmt + '/' + measurement + '-' + month + '/{z}/{x}/{y}.jpeg';
        } else {
            return 'data/' + data_source + '/' + date_range + '/' + fmt + '/' + measurement + '/{z}/{x}/{y}.jpeg';
        }
    } else {
        if (month) {
            return 'data/' + data_source + '/' + date_range + '/' + measurement + '-' + month + '.' + fmt;
        } else {
            return 'data/' + data_source + '/' + date_range + '/' + measurement + '.' + fmt;
        }
    }
}

/**
 * Rounds a number to the nearest resolution in degrees.
 *
 * If offset is not zero, the number will be rounded to the
 * nearest resolution plus the offset. If you set offset to 0.25,
 * this would allow you to round to the nearest 0.25 or 0.75 in
 * the case of the gridded NOAA data.
 */
function roundCoordinateToResolution(coord)
{
    return Math.round((coord - DELTA_OFFSET) / DELTA) * DELTA + DELTA_OFFSET;
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

    return 'api/monthly-normals/' + data_source + '/' + date_range + '/' + lat + '/' + lon;
}

/**
 * Fetches data for the specified coordinates and date range.
 */
async function fetchClimateDataForCoords(data_source, date_range, lat, lon)
{
    const url = climateDataUrlForCoords(data_source, date_range, lat, lon);

    const response = await fetch(url);
    let data = await response.json();

    data = populateMissingTemperatureData(data);

    /* The WorldClim data doesn't have the annual measurements but NOAA does. */
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
    const month_select = document.getElementById('month');

    const data_source = data_source_select.value;
    const date_range = date_range_select.value;
    const measurement = measurement_select.value;
    const month = month_select.value;

    tile_layer.setUrl(
        climateDataUrl(data_source, date_range, measurement, month, 'tiles')
    );
}

/**
 * Updates the image layer for the climate filters in the document.
 */
function updateImageLayer(image_layer)
{
    const data_source_select = document.getElementById('data-source');
    const date_range_select = document.getElementById('date-range');
    const measurement_select = document.getElementById('measurement');
    const month_select = document.getElementById('month');

    const data_source = data_source_select.value;
    const date_range = date_range_select.value;
    const measurement = measurement_select.value;
    const month = month_select.value;

    image_layer.setUrl(
        climateDataUrl(data_source, date_range, measurement, month, 'png'),
    );
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
    const month_select = document.getElementById('month');

    const data_source = data_source_select.value;
    const date_range = date_range_select.value;
    const measurement = measurement_select.value;
    const month = month_select.value;

    return L.tileLayer(
        climateDataUrl(data_source, date_range, measurement, month, 'tiles'),
        {
            attribution: dataSourceAttribution(data_source_select),
            maxZoom: 12,
            maxNativeZoom: 6,
            opacity: 0.6,
            bounds: [[85.051129, -180], [-85.051129 + DELTA/2, 180 - DELTA/2]],
        }
    );
}

/**
 * Creates an image layer with climate data based on the inputs.
 * This shows the differences between different regions' climates in a visual way.
 *
 * @return map layer
 */
function createImageLayer()
{
    const data_source_select = document.getElementById('data-source');
    const date_range_select = document.getElementById('date-range');
    const measurement_select = document.getElementById('measurement');
    const month_select = document.getElementById('month');

    const data_source = data_source_select.value;
    const date_range = date_range_select.value;
    const measurement = measurement_select.value;
    const month = month_select.value;

    return L.imageOverlay(
        climateDataUrl(data_source, date_range, measurement, month, 'png'),
        [[85.051129, -180], [-85.051129 + DELTA/2, 180 - DELTA/2]],
        {
            'opacity': 0.6
        }
    );
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
            return colours;

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
function updateClimateChart(data, temp_chart, precip_chart)
{
    const average_temperature = Math.round(data['tavg'][0][0] * 10) / 10;
    const total_precipitation = Math.round(data['precip'][0][0] * 10) / 10;
    document.getElementById('average-temperature').textContent = average_temperature;
    document.getElementById('total-precipitation').textContent = total_precipitation;

    if (temp_chart !== undefined) {
        temp_chart.destroy();
    }
    temp_chart = createClimateChart(
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

    if (precip_chart !== undefined) {
        precip_chart.destroy();
    }
    precip_chart = createClimateChart(
        [data['precip']],
        'mm',
        ['Precipitation (mm)'],
        'bar',
        'location-precipitation-chart'
    );

    return [temp_chart, precip_chart];
}

/**
 * Highlights the correct measurement button.
 */
function highlightMeasurementButton(measurement)
{
    let selected_button, unselected_buttons;

    switch (measurement) {
        case 'temperature-avg':
            selected_button = document.getElementById('temperature-button');
            unselected_buttons = [
                document.getElementById('precipitation-button'),
            ];
            break;

        case 'precipitation':
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
 * Populates the data sources
 */
async function populateDataSources(data_source_select, date_range_select)
{
    const date_range_option = date_range_select.options[date_range_select.selectedIndex];
    const date_range = date_range_option.value;

    const data_sources = await fetchDataSources(date_range);

    /* Try to preserve the already selected data source, if any. */
    const selected_option = data_source_select.options[data_source_select.selectedIndex];
    const selected_data_source = selected_option.value;

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

        data_source_select.add(option);

        if (option.value == selected_data_source) {
            data_source_select.selectedIndex = i;
        }
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
 * Shows the location climate container.
 */
function showLocationClimate()
{
    document.getElementById('location-climate').style.display = 'block';
    document.getElementById('close-location-climate-container').style.display = 'block';
}

/**
 * Hides the location climate container.
 */
function hideLocationClimate()
{
    document.getElementById('location-climate').style.display = 'none';
    document.getElementById('close-location-climate-container').style.display = 'none';
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
 * Loads the climate map.
 */
window.onload = function() {
    /* Fetch GeoJSON */
    var climate_map = L.map('climate-map').setView([0, 0], 2);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: 'Map tiles &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(climate_map);

    var climate_tile_layer;
    const location_marker = L.marker([0, 0]);

    var temp_chart, precip_chart;
    var clicked_lat, clicked_lon;

    const data_source_select = document.getElementById('data-source');
    const date_range_select = document.getElementById('date-range');
    const measurement_select = document.getElementById('measurement');
    const month_select = document.getElementById('month');

    populateDateRanges(date_range_select).then(function() {
        populateDataSources(data_source_select, date_range_select).then(function() {
            climate_tile_layer = createTileLayer().addTo(climate_map);
        });
    });

    highlightMeasurementButton('temperature-avg');

    /**
     * Handle changes to the filters. We will update the map's colours.
     */
    const update_tiles_and_chart = function() {
        updateTileLayer(climate_tile_layer);

        if (clicked_lat && clicked_lon) {
            const data_source = data_source_select.value;
            const date_range = date_range_select.value;

            fetchClimateDataForCoords(data_source, date_range, clicked_lat, clicked_lon).then(function(data) {
                [temp_chart, precip_chart] = updateClimateChart(data, temp_chart, precip_chart);
            });
        }
    };

    function change_data_source() {
        update_tiles_and_chart();

        climate_tile_layer.remove();
        climate_tile_layer.options.attribution = dataSourceAttribution(data_source_select);
        climate_tile_layer.addTo(climate_map);
    }

    data_source_select.onchange = change_data_source;

    date_range_select.onchange = function() {
        populateDataSources(data_source_select, date_range_select).then(change_data_source);
        document.getElementById('date-range-slider').value = date_range_select.selectedIndex;
    };

    measurement_select.onchange = function() {
        updateTileLayer(climate_tile_layer);
        highlightMeasurementButton(measurement_select.value);
    };

    month_select.onchange = function() {
        updateTileLayer(climate_tile_layer);
    };

    /**
     * Handle clicks on the climate map. We will show a bunch of information
     * about that particular location's climate.
     */

    function show_climate_chart(lat, lon) {
        const data_source = data_source_select.value;
        const date_range = date_range_select.value;

        fetchClimateDataForCoords(data_source, date_range, lat, lon).then(function(data) {
            location_marker.setLatLng([lat, lon]).addTo(climate_map).on('click', showLocationClimate);

            [temp_chart, precip_chart] = updateClimateChart(data, temp_chart, precip_chart);

            showLocationClimate();
        });
    }

    climate_map.on('click', function(e) {
        clicked_lat = e.latlng.lat;
        clicked_lon = e.latlng.lng;

        show_climate_chart(clicked_lat, clicked_lon);
    });

    document.getElementById('close-location-climate').onclick = function() {
        hideLocationClimate();
    };

    async function doSearch() {
        const search_input = document.getElementById('search');
        const search_query = search_input.value;

        if (search_query) {
            const data = await search(search_query);
            const lat = data['lat'];
            const lon = data['lon'];

            document.getElementById('search-container').style.display = 'none';

            climate_map.setView([lat, lon], 8);
            show_climate_chart(lat, lon);
        }
    }

    document.getElementById('search-button').onclick = doSearch;
    document.getElementById('search').addEventListener("keyup", function(event) {
        /* Credit: https://www.w3schools.com/howto/howto_js_trigger_button_enter.asp */
        event.preventDefault();
        if (event.keyCode === 13) {
            doSearch();
        };
    });

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
        setDropDown('measurement', 'temperature-avg');
        updateTileLayer(climate_tile_layer);
        highlightMeasurementButton('temperature-avg');
    };

    document.getElementById('precipitation-button').onclick = function() {
        setDropDown('measurement', 'precipitation');
        updateTileLayer(climate_tile_layer);
        highlightMeasurementButton('precipitation');
    };

    document.getElementById('about-button').onclick = function() {
        const about_div = document.getElementById('about');
        about_div.style.display = (about_div.style.display == 'none') ? 'block' : 'none';
    };

    const date_range_slider = document.getElementById('date-range-slider');

    date_range_slider.onchange = function(e) {
        date_range_select.selectedIndex = e.target.value;
        populateDataSources(data_source_select, date_range_select).then(change_data_source);
        hideDateRangeSliderTooltip();
    };

    date_range_slider.onmousedown = updateDateRangeSliderTooltip;
    date_range_slider.onmouseup = hideDateRangeSliderTooltip;
    date_range_slider.oninput = updateDateRangeSliderTooltip;
    date_range_slider.onkeydown = updateDateRangeSliderTooltip;
};
