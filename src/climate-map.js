/**
 * Main climate map javascript.
 *
 * Copyright (c) 2019 Carlos Torchia
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
 * Returns the URL for the specified climate data.
 */
function climateDataUrl(date_range, measurement, month, fmt)
{
    if (month) {
        return 'data/' + date_range + '/' + measurement + '-' + month + '.' + fmt;
    } else {
        return 'data/' + date_range + '/' + measurement + '.' + fmt;
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
    const res = 1/12;
    const offset = 0;

    return Math.round((coord - offset) / res) * res + offset;
}

/**
 * Returns the URL for the specified climate data by latitude and longitude.
 */
function climateDataUrlForCoords(date_range, lat, lon)
{
    /* Round the coordinate again because it can be infinitie digits.
     * We times and divide by 100 to round to the nearest hundredth. */
    let rounded_lat = Math.round(roundCoordinateToResolution(lat) * 100) / 100;
    let rounded_lon = Math.round(roundCoordinateToResolution(lon) * 100) / 100;

    const lat_index = Math.floor(rounded_lat);
    const lon_index = Math.floor(rounded_lon);

    /* Whole-number coordinates need to end with ".0". Python outputs them like that
     * and JavaScript outputs them as integers without decimal. */
    rounded_lat = (rounded_lat * 10 % 10 == 0) ? rounded_lat.toFixed(1) : rounded_lat;
    rounded_lon = (rounded_lon * 10 % 10 == 0) ? rounded_lon.toFixed(1) : rounded_lon;

    const coord_index = rounded_lat + '_' + rounded_lon;

    return 'data/' + date_range + '/coords/' + lat_index + '/' + lon_index + '/' + coord_index + '.json';
}

/**
 * Fetches data for the specified coordinates and date range.
 */
async function fetchClimateDataForCoords(date_range, lat, lon)
{
    const url = climateDataUrlForCoords(date_range, lat, lon);
    console.log(url);

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

    return data
}

/**
 * Updates the climate layer for the climate filters in the document.
 */
async function updateClimateLayer(climate_layer)
{
    const date_range_select = document.getElementById('date-range');
    const measurement_select = document.getElementById('measurement');
    const month_select = document.getElementById('month');

    const date_range = date_range_select.value;
    const measurement = measurement_select.value;
    const month = month_select.value;

    climate_layer.setUrl(
        climateDataUrl(date_range, measurement, month, 'png')
    );
}

/**
 * Create the climate layer. This shows the differences between
 * different regions' climates in a visual way.
 *
 * @return map layer
 */
function createClimateLayer()
{
    const date_range_select = document.getElementById('date-range');
    const measurement_select = document.getElementById('measurement');
    const month_select = document.getElementById('month');

    const date_range = date_range_select.value;
    const measurement = measurement_select.value;
    const month = month_select.value;

    return L.imageOverlay(
        climateDataUrl(date_range, measurement, month, 'png'),
        [[85, -180], [-85 - 3/12/8, 180 - 1/12]],
        {
            'opacity': 0.8
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
                label: label,
                data: values,
                backgroundColor: colours,
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
            data['tavg'][month] = [(tmin + tmax) / 2, units];
        }

        if (tmin === null && tavg !== null && tmax !== null) {
            let units = data['tavg'][month][1];
            data['tmin'][month] = [2 * tavg - tmax, units];
        }

        if (tmax === null && tavg !== null && tmin !== null) {
            let units = data['tavg'][month][1];
            data['tmax'][month] = [2 * tavg - tmin, units];
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
 * Loads the climate map.
 */
window.onload = async function() {
    /* Fetch GeoJSON */
    var climate_map = L.map('climate-map').setView([0, 0], 3);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: 'Map tiles &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors | Climate data &copy; <a href="http://worldclim.org">WorldClim</a>'
    }).addTo(climate_map);

    const climate_layer = createClimateLayer().addTo(climate_map);
    const location_marker = L.marker([0, 0]);

    var temp_chart, precip_chart;
    var clicked_lat, clicked_lon;

    /**
     * Handle changes to the filters. We will update the map's colours.
     */
    const date_range_select = document.getElementById('date-range');
    const measurement_select = document.getElementById('measurement');
    const month_select = document.getElementById('month');

    date_range_select.onchange = function () {
        updateClimateLayer(climate_layer);

        if (clicked_lat && clicked_lon) {
            const date_range_select = document.getElementById('date-range');
            const date_range = date_range_select.value;

            fetchClimateDataForCoords(date_range, clicked_lat, clicked_lon).then(function(data) {
                [temp_chart, precip_chart] = updateClimateChart(data, temp_chart, precip_chart);
            });
        }
    };

    measurement_select.onchange = function () {
        updateClimateLayer(climate_layer);
    };

    month_select.onchange = function () {
        updateClimateLayer(climate_layer);
    };

    /**
     * Handle clicks on the climate map. We will show a bunch of information
     * about that particular location's climate.
     */

    climate_map.on('click', function(e) {
        clicked_lat = e.latlng.lat;
        clicked_lon = e.latlng.lng;

        const date_range_select = document.getElementById('date-range');
        const date_range = date_range_select.value;

        fetchClimateDataForCoords(date_range, clicked_lat, clicked_lon).then(function(data) {
            location_marker.setLatLng(e.latlng).addTo(climate_map).on('click', showLocationClimate);

            [temp_chart, precip_chart] = updateClimateChart(data, temp_chart, precip_chart);

            showLocationClimate();
        });
    });

    document.getElementById('close-location-climate').onclick = function() {
        hideLocationClimate();
    };
};
