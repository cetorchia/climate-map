/**
 * Main climate map javascript.
 */

window.onload = async function() {
    /* Fetch GeoJSON */
    var climate_map = L.map('climate-map').setView([39.75621, -104.99404], 5);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors | <a href="https://www.esrl.noaa.gov/psd/data/gridded/">NOAA/OAR/ESRL PSD, Boulder, Colorado, USA</a>'
    }).addTo(climate_map);

    try {
        const response = await fetch('climate.json');
        const geojson = await response.json();
        L.geoJSON(geojson).addTo(climate_map);
    } catch (error) {
        console.error(error);
    }
};
