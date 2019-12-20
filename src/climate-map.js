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
    const lat_index = Math.floor(lat);
    const lon_index = Math.floor(lon);

    /* Round the coordinate again because it can be infinitie digits. */
    const rounded_lat = roundCoordinateToResolution(lat).toFixed(2);
    const rounded_lon = roundCoordinateToResolution(lon).toFixed(2);

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
    const data = await response.json();

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
        [[85, -180], [-85 - 1/12, 180]],
        {
            'opacity': 0.8
        }
    );
}

/**
 * Returns the colours for each month based on the value
 * and units. This gives a visual sense of the temperature
 * or precipitation amount.
 */
function coloursForMonthData(values, units)
{
    let colours = [];
    switch (units) {
        case 'degC':
            for (let i = 0; i <= values.length - 1; i++) {
                const value = values[i];
                let red, green, blue;

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

                colours.push('rgb(' + red + ',' + green + ',' + blue + ')');
            }
            return colours;

        case 'mm':
            for (let i = 0; i <= values.length - 1; i++) {
                const value = values[i];
                let red, green, blue;

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

                colours.push('rgb(' + red + ',' + green + ',' + blue + ')');
            }
            return colours;

        default:
            return '#22b';
    }
}

/**
 * Shows a climate chart with the specified data.
 *
 * @return Chart
 */
function createClimateChart(data, units, label, canvas_id)
{
    const ctx = document.getElementById(canvas_id).getContext('2d');

    /* Collect temperature means for each month in a linear fashion. */
    let values = [];
    for (let i = 1; i <= 12; i++) {
        if (data[i][1] !== units) {
            throw new Error('Expected ' + units + ', got ' + data[i][1]);
        }
        values.push(data[i][0]);
    }

    /* Create the chart. */
    const chart = new Chart(ctx, {
        type: 'bar',
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
            datasets: [
                {
                    label: label,
                    data: values,
                    backgroundColor: coloursForMonthData(values, units),
                }
            ],
        },
        options: {
            scales: {
                yAxes: [{
                    ticks: {
                        beginAtZero: true
                    }
                }]
            }
        },
    });

    return chart;
}

/**
 * Returns the average of all the temperatures in the specified object.
 */
function getAverageTemperature(temperatures)
{
    let sum = 0;

    for (let i = 1; i <= 12; i++) {
        sum += temperatures[i][0];
    }

    return sum / 12;
}

/**
 * Returns the total of all the precipitations in the specified object.
 */
function getTotalPrecipitation(precipitations)
{
    let sum = 0;

    for (let i = 1; i <= 12; i++) {
        sum += precipitations[i][0];
    }

    return sum;
}

/**
 * Updates the climate chart.
 */
function updateClimateChart(data, temp_chart, precip_chart)
{
    /* The WorldClim data doesn't have the annual measurements but NOAA does. */
    if (data['tavg'][0] === undefined) {
        data['tavg'][0] = getAverageTemperature(data['tavg']);
    }

    if (data['precip'][0] === undefined) {
        data['precip'][0] = getTotalPrecipitation(data['precip']);
    }

    document.getElementById('average-temperature').textContent = data['tavg'][0][0];
    document.getElementById('total-precipitation').textContent = data['precip'][0][0];

    if (temp_chart !== undefined) {
        temp_chart.destroy();
    }
    temp_chart = createClimateChart(
        data['tavg'],
        'degC',
        'Temperature (°C)',
        'location-temperature-chart'
    );

    if (precip_chart !== undefined) {
        precip_chart.destroy();
    }
    precip_chart = createClimateChart(
        data['precip'],
        'mm',
        'Precipitation (mm)',
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

        console.log('[' + clicked_lat + ', ' + clicked_lon + ']');

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
