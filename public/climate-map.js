/**
 * Main climate map javascript.
 */

/**
 * Returns the colour for the specified degrees Celsius.
 */
function degreesCelsiusColour(amount, month) {
    if (!month) {
        amount = amount - 10;
    }
    if (amount > 35) {
        return "#ff0000";
    } else if (amount > 30) {
        return "#ff2222";
    } else if (amount > 25) {
        return "#ff4444";
    } else if (amount > 20) {
        return "#ff6666";
    } else if (amount > 15) {
        return "#ff8888";
    } else if (amount > 10) {
        return "#ffaaaa";
    } else if (amount > 5) {
        return "#ffcccc";
    } else if (amount > 0) {
        return "#ffeeee";
    } else if (amount < -35) {
        return "#0000ff";
    } else if (amount < -30) {
        return "#2222ff";
    } else if (amount < -25) {
        return "#4444ff";
    } else if (amount < -20) {
        return "#6666ff";
    } else if (amount < -15) {
        return "#8888ff";
    } else if (amount < -10) {
        return "#aaaaff";
    } else if (amount < -5) {
        return "#ccccff";
    } else {
        return "#eeeeff";
    }
}

/**
 * Returns the colour for the specified mm of precipitation.
 */
function precipitationMillimetresColour(amount, month) {
    if (month) {
        amount = amount * 12;
    }
    if (amount > 2000) {
        return "#44ff44";
    } else if (amount > 1000) {
        return "#88ff88";
    } else if (amount > 500) {
        return "#ccffcc";
    } else if (amount < 100) {
        return "#ffff44";
    } else if (amount < 250) {
        return "#ffff88";
    } else {
        return "#ffffcc";
    }
}

/**
 * Returns the style for the specified climate geoJSON.
 */
function styleClimateFeature(feature) {
    const amount = feature.properties.amount;
    const units = feature.properties.units;
    var colour;

    switch (units) {
        case 'degC':
            colour = degreesCelsiusColour(amount, feature.properties.month);
            break;

        case 'mm':
            colour = precipitationMillimetresColour(amount, feature.properties.month);
            break;
    }

    return {
        'stroke': feature.geometry.type != 'Polygon',
        'fillOpacity': 0.5,
        'color': colour
    };
}

/**
 * Returns human-friendly text for the specified measurement units.
 */
function unitText(units) {
    switch (units) {
        case 'degC':
            return '&#176;C';

        default:
            return units;
    }
}

/**
 * This function executes for each climate geoJSON.
 */
function onEachClimateFeature(feature, layer) {
    const amount = feature.properties.amount;
    const units = feature.properties.units;
    const comment = feature.properties.comment;
    const popupText = amount + ' ' + unitText(units) + ' <br> ' + comment;

    layer.bindPopup(popupText);
}

/**
 * Returns the geoJSON for the specified climate filters.
 */
async function fetchClimateData(date_range, measurement, month) {
    var url;

    if (month) {
        url = 'data/' + date_range + '/' + measurement + '-' + month + '.json';
    } else {
        url = 'data/' + date_range + '/' + measurement + '.json';
    }

    const response = await fetch(url);
    const geojson = await response.json();

    return geojson;
}

/**
 * Updates the climate layer for the specified climate filters.
 */
async function updateClimateLayerWith(climate_layer, date_range, measurement, month) {
    try {
        const geojson = await fetchClimateData(date_range, measurement, month);
        climate_layer.clearLayers();
        climate_layer.addData(geojson);
    } catch (error) {
        console.error(error);
    }
}

/**
 * Updates the climate layer for the climate filters in the document.
 */
async function updateClimateLayer(climate_layer) {
    const date_range_select = document.getElementById('date-range');
    const measurement_select = document.getElementById('measurement');
    const month_select = document.getElementById('month');

    const date_range = date_range_select.value;
    const measurement = measurement_select.value;
    const month = month_select.value;

    updateClimateLayerWith(climate_layer, date_range, measurement, month);
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

    const climate_layer = L.geoJSON([], {
        style: styleClimateFeature,
        onEachFeature: onEachClimateFeature
    }).addTo(climate_map);

    updateClimateLayer(climate_layer);

    const date_range_select = document.getElementById('date-range');
    const measurement_select = document.getElementById('measurement');
    const month_select = document.getElementById('month');

    date_range_select.onchange = async function () {
        updateClimateLayer(climate_layer);
    };

    measurement_select.onchange = async function () {
        updateClimateLayer(climate_layer);
    };

    month_select.onchange = async function () {
        updateClimateLayer(climate_layer);
    };
};
