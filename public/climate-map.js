/**
 * Main climate map javascript.
 */

function styleClimateFeatures(feature) {
    const amount = feature.properties.amount;

    switch (feature.properties.units) {
        case 'degC':
            if (amount > 20) {
                return {color: "#ff4444"};
            } else if (amount > 10) {
                return {color: "#ff8888"};
            } else if (amount > 0) {
                return {color: "#ffcccc"};
            } else if (amount < -20) {
                return {color: "#4444ff"};
            } else if (amount < -10) {
                return {color: "#8888ff"};
            } else {
                return {color: "#ccccff"};
            }

        case 'mm':
            if (amount > 2000) {
                return {color: "#44ff44"};
            } else if (amount > 1000) {
                return {color: "#88ff88"};
            } else if (amount > 500) {
                return {color: "#ccffcc"};
            } else if (amount < 100) {
                return {color: "#ffff44"};
            } else if (amount < 250) {
                return {color: "#ffff88"};
            } else {
                return {color: "#ffffcc"};
            }
    }
}

window.onload = async function() {
    /* Fetch GeoJSON */
    var climate_map = L.map('climate-map').setView([49.767, -97.827], 3);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: 'Map tiles &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors | Climate data &copy; <a href="https://www.esrl.noaa.gov/psd/data/gridded/">NOAA/OAR/ESRL PSD</a>'
    }).addTo(climate_map);

    const climate_layer = L.geoJSON([], {
        style: styleClimateFeatures
    }).addTo(climate_map);

    try {
        const response = await fetch('data/1980-2010/temperature.json');
        const geojson = await response.json();

        climate_layer.addData(geojson);
    } catch (error) {
        console.error(error);
    }
};
