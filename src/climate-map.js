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
 * Rounds a number to the nearest 0.25 or 0.75
 */
function roundCoordinate(coord)
{
    if (coord >= 0) {
        const decimal = coord % 1;
        return Math.floor(coord) + (decimal >= 0.5 ? 0.75 : 0.25);
    } else {
        const decimal = -coord % 1;
        return Math.floor(coord) + 1 - (decimal >= 0.5 ? 0.75 : 0.25);
    }
}

/**
 * Returns the URL for the specified climate data by latitude and longitude.
 */
function climateDataUrlForCoords(date_range, lat, lon)
{
    const lat_grp = Math.floor(lat / 10) * 10;
    const lon_grp = Math.floor(lon / 10) * 10;

    const rounded_lat = roundCoordinate(lat);
    const rounded_lon = roundCoordinate(lon);

    const coords = rounded_lat + '_' + rounded_lon;

    return 'data/' + date_range + '/coords/' + lat_grp + '/' + lon_grp + '/' + coords + '.json';
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
        [[85, -180], [-85, 180]],
        {
            'opacity': 0.8
        }
    );
}

/**
 * Shows a climate chart with the specified data.
 *
 * @return Chart
 */
function createClimateChart(data)
{
    const ctx = document.getElementById('location-climate-chart').getContext('2d');

    /* Collect temperature means for each month in a linear fashion. */
    let temps = [];
    const air_data = data['air'];
    for (let i = 1; i <= 12; i++) {
        if (air_data[i][1] != 'degC') {
            throw new Error('Expected air temp in degC, got ' + air_data[i][1]);
        }
        temps.push(air_data[i][0]);
    }

    /* Collect precipitation totals for each month in a linear fashion. */
    let precips = [];
    const precip_data = data['precip'];
    for (let i = 1; i <= 12; i++) {
        if (precip_data[i][1] != 'mm') {
            throw new Error('Expected precip in mm, got ' + precip_data[i][1]);
        }
        precips.push(precip_data[i][0]);
    }

    /* Create the chart. */
    const chart = new Chart(ctx, {
        'type': 'bar',
        'data': {
            'labels': [
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
            'datasets': [
                {
                    'label': 'Temperature (°C)',
                    'data': temps,
                    'order': 2,
                    'backgroundColor': '#e22',
                    'yAxisId': 'y-axis-left',
                },
                {
                    'label': 'Precipitation (mm)',
                    'data': precips,
                    'type': 'line',
                    'order': 1,
                    'backgroundColor': '#22e',
                    'fill': false,
                    'yAxisId': 'y-axis-right',
                }
            ],
            'scales': {
                'yAxes': [
                    {
                        'type': 'linear',
                        'display': true,
                        'position': 'left',
                        'id': 'y-axis-left',
                    },
                    {
                        'type': 'linear',
                        'display': true,
                        'position': 'right',
                        'id': 'y-axis-right',
                    },
                ],
            },
        },
    });

    return chart;
}

/**
 * Loads the climate map.
 */
window.onload = async function() {
    /* Fetch GeoJSON */
    var climate_map = L.map('climate-map').setView([49.767, -97.827], 3);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: 'Map tiles &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors | Climate data &copy; <a href="https://www.esrl.noaa.gov/psd/data/gridded/">NOAA/OAR/ESRL PSD</a>'
    }).addTo(climate_map);

    const climate_layer = createClimateLayer().addTo(climate_map);
    const location_marker = L.marker([0, 0]);

    /**
     * Handle changes to the filters. We will update the map's colours.
     */
    const date_range_select = document.getElementById('date-range');
    const measurement_select = document.getElementById('measurement');
    const month_select = document.getElementById('month');

    date_range_select.onchange = function () {
        updateClimateLayer(climate_layer);
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
    var climate_chart;

    climate_map.on('click', function(e) {
        const lat = e.latlng.lat;
        const lon = e.latlng.lng;

        const date_range_select = document.getElementById('date-range');
        const date_range = date_range_select.value;

        const promise = fetchClimateDataForCoords(date_range, lat, lon);

        promise.then(function(data) {
            location_marker.setLatLng(e.latlng).addTo(climate_map);

            if (climate_chart !== undefined) {
                climate_chart.destroy();
            }
            climate_chart = createClimateChart(data);

            /* Show the location climate div. */
            document.getElementById('location-climate').style.display = 'block';
        });
    });

    document.getElementById('close-location-climate').onclick = function() {
        /* Hide the location climate div. */
        document.getElementById('location-climate').style.display = 'none';
    };
};
