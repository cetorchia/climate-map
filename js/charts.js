/**
 * Shows charts and averages for a specific location's climate.
 *
 * Copyright (c) 2020 Carlos Torchia
 */

import { convertDataUnits, getUnitLabel } from './units.js';
import { getMeasurementLabel } from './measurements.js';
import { updatePageState } from './page-state.js';
import { fetchClimateDataForCoords } from './api.js';

import chart_html from '../html/charts.html';

import APP from './app.js';

/**
 * Returns the colour for the specified value with units.
 */
function colourForValueAndUnits(value, measurement, units)
{
    let red, green, blue;

    switch (units) {
        case 'degF':
            value = (value - 32) * 5 / 9;

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

        case 'in':
            value = value * 25.4;

        case 'mm':
            switch (measurement) {
                case 'precip':
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

                case 'et':
                case 'potet':
                    if (value < 25) {
                        red = 100;
                        green = 100;
                        blue = 255;
                    } else if (value < 80) {
                        red = 2.25 * value;
                        green = 255;
                        blue = red;
                    } else {
                        red = Math.min(200 + (value - 80) / 7, 250);
                        green = 230;
                        blue = Math.max(200 - (value - 80) * 3 / 7, 0);
                    }
                    return 'rgb(' + red + ',' + green + ',' + blue + ')';
            }


        default:
            return '#22b';
    }
}

/**
 * Returns the colours for each month based on the value
 * and units. This gives a visual sense of the temperature
 * or precipitation amount.
 */
function coloursForMonthData(values, measurement, units)
{
    let colours = [];

    for (let i = 0; i <= values.length - 1; i++) {
        const value = values[i];
        const colour = colourForValueAndUnits(value, measurement, units);
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
function createClimateChart(datasets, measurement, units, labels, type, canvas_id)
{
    const ctx = document.getElementById(canvas_id).getContext('2d');

    /* Collect temperature means for each month in a linear fashion. */
    let chart_datasets = [];

    if (type == 'bar' && datasets.length == 3) {
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

        const colours = coloursForMonthData(mean_values, measurement, units);
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

            const colours = coloursForMonthData(values, measurement, units);
            const avg_colour = colourForValueAndUnits(data[0][0], measurement, data[0][1]);

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
 * Updates the climate chart with the specified data.
 */
export async function updateClimateCharts(data)
{
    data = convertDataUnits(data, APP.units);

    updateNontemporalValue(data, 'elevation', 'elevation');

    updateClimateChart(data, 'tavg', 'location-temperature-chart', 'average-temperature');
    updateClimateChart(data, 'precip', 'location-precipitation-chart', 'total-precipitation');
    updateClimateChart(data, 'potet', 'location-potet-chart', 'total-potet');

    const data_source_select = document.getElementById('data-source');
    document.getElementById('chart-source').innerHTML = APP.attribution;
}

/**
 * Updates the climate chart for the specified data and measurement.
 */
function updateClimateChart(data, measurement, chart_canvas_id, average_span_id)
{
    if (APP.charts[measurement] !== undefined) {
        APP.charts[measurement].destroy();
    }

    if (data[measurement] === undefined) {
        document.getElementById(average_span_id).parentNode.style.display = 'none';
        document.getElementById(chart_canvas_id).style.display = 'none';
        return;
    } else {
        document.getElementById(average_span_id).parentNode.style.display = 'block';
        document.getElementById(chart_canvas_id).style.display = 'block';
    }

    const average = Math.round(data[measurement][0][0] * 10) / 10;

    const units = data[measurement][0][1];
    const unit_label = getUnitLabel(units);

    document.getElementById(average_span_id).textContent = average + ' ' + unit_label;

    let chart_data, chart_labels;
    
    if (measurement == 'tavg') {
        chart_data = [
            data['tavg'],
            ('tmin' in data ? data['tmin'] : {}),
            ('tmax' in data ? data['tmax'] : {}),
        ];
        chart_labels = [
            'Mean Temperature (' + unit_label + ')',
            'Min Temperature (' + unit_label + ')',
            'Max Temperature (' + unit_label + ')',
        ];
    } else {
        chart_data = [data[measurement]];
        chart_labels = [getMeasurementLabel(measurement) + ' (' + unit_label + ')'];
    }

    APP.charts[measurement] = createClimateChart(
        chart_data,
        measurement,
        units,
        chart_labels,
        'bar',
        chart_canvas_id
    );
}

/**
 * Updates a nontemporal value like elevation displayed in the location climate
 * window from the specified response data.
 */
function updateNontemporalValue(data, measurement, span_id)
{
    if (data[measurement] === undefined) {
        document.getElementById(span_id).parentNode.style.display = 'none';
        return;
    } else {
        document.getElementById(span_id).parentNode.style.display = 'block';
    }

    const value = Math.round(data[measurement][0] * 10) / 10;

    const units = data[measurement][1];
    const unit_label = getUnitLabel(units);

    document.getElementById(span_id).textContent = value + ' ' + unit_label;
}

/**
 * Hides the location climate container.
 */
export function hideClimateCharts()
{
    document.getElementById('location-climate').style.display = 'none';
}

/**
 * Shows the location climate container.
 */
export function showClimateCharts()
{
    document.getElementById('location-climate').style.display = 'block';
}

/**
 * Loads the HTML for the charts.
 */
export function loadChartHTML()
{
    const template = document.createElement('template');
    template.innerHTML = chart_html;
    document.getElementsByTagName('body')[0].append(template.content);

    document.getElementById('close-location-climate').onclick = function() {
        hideClimateCharts();
        updatePageState();
    };
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
 * Shows the user climate charts for the specified location.
 */
export function loadLocationClimate(lat, lon, location_title)
{
    const data_source_select = document.getElementById('data-source');
    const date_range_select = document.getElementById('date-range');
    const data_source = data_source_select.value;
    const date_range = date_range_select.value;

    return fetchClimateDataForCoords(data_source, date_range, lat, lon).then(function(data) {
        APP.location_marker.setLatLng([lat, lon]).addTo(APP.climate_map).on('click', function() {
            showLocationTitle(location_title);
            showClimateCharts();
            updatePageState(lat, lon, location_title);
        });

        APP.data = data;
        updateClimateCharts(data);

        showLocationTitle(location_title);
        showClimateCharts();

        APP.clicked_lat = lat;
        APP.clicked_lon = lon;

        return [lat, lon, location_title];
    });
}

/**
 * Refreshes the data already shown to the user,
 * if the user has previously clicked on a location.
 *
 * This will skip creating a marker that should already be on the map.
 */
export function updateLocationClimate()
{
    if (APP.clicked_lat && APP.clicked_lon) {
        const data_source_select = document.getElementById('data-source');
        const date_range_select = document.getElementById('date-range');
        const data_source = data_source_select.value;
        const date_range = date_range_select.value;

        fetchClimateDataForCoords(data_source, date_range, APP.clicked_lat, APP.clicked_lon).then(function(data) {
            APP.data = data;
            updateClimateCharts(data);
        });
    }
}

/**
 * Shows the climate of the specified location and
 * updates the page state. This should be called when the
 * user clicks on the map.
 */
export function viewLocationClimate(lat, lon, display_name)
{
    return loadLocationClimate(lat, lon, display_name).then(([lat, lon, display_name]) => {
        updatePageState(lat, lon, display_name);
    });
}
