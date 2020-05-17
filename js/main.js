/**
 * Main climate map javascript.
 *
 * Copyright (c) 2020 Carlos Torchia
 */

import CONFIG from '../config/config.json';
import '../css/style.css';

import { createClimateTileLayer, updateClimateTileLayer, createBaseMapLayer } from './tiles.js';
import { showError } from './error.js';
import { handleSearch } from './search.js';
import { updateClimatesOfPlaces, setClimatesOfPlaces } from './places.js';
import { viewLocationClimate, updateClimateCharts, updateLocationClimate, loadChartHTML } from './charts.js';
import { handleUnits, updateUnitsButton, fetchPreferredUnits } from './units.js';

import {
    getMeasurementLabel,
    highlightMeasurementButton,
    handleMeasurementChanges
} from './measurements.js';

import { getPeriodLabel } from './periods.js';
import { updateLegend } from './legend.js';
import { goToPageState, goToURL } from './page-state.js';
import { fetchClimateDataForCoords } from './api.js';

import {
    populateDataSources,
    updateLastDataSource,
    getLastDataSource,
    updateSSPButton,
    updateSSP,
} from './data-sources.js';

import {
    populateDateRanges,
    handleDateRangeChanges,
} from './date-ranges.js';

import { handleAbout } from './about.js';
import { loadControlsHtml } from './controls.js';

import PLACE_MARKER_ICON from '../images/marker.png';

import APP from './app.js';

let L, Chart;

async function importDependencies()
{
    try {
        const {default: L} = await import(/* webpackChunkName: "leaflet" */ 'leaflet/dist/leaflet-src.js');
        const {default: Chart} = await import(/* webpackChunkName: "chartjs" */ 'chart.js/dist/Chart.bundle.js');

        await import(/* webpackChunkName: "leaflet" */ 'leaflet/dist/leaflet.css');

        /* Enable this if you want to use mapboxGL */
        //await import(/* webpackChunkName: "mapbox-gl-leaflet" */ 'mapbox-gl-leaflet');
        //await import('mapbox-gl/dist/mapbox-gl.css');

        // Hack so that leaflet's images work after going through webpack
        // @see https://github.com/PaulLeCam/react-leaflet/issues/255#issuecomment-388492108
        const {default: marker} = await import(/* webpackChunkName: "leaflet" */ 'leaflet/dist/images/marker-icon.png');
        const {default: marker2x} = await import(/* webpackChunkName: "leaflet" */ 'leaflet/dist/images/marker-icon-2x.png');
        const {default: markerShadow} = await import(/* webpackChunkName: "leaflet" */ 'leaflet/dist/images/marker-shadow.png');

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

const PLACE_MARKER_ICON_SIZE = [36, 36];
const PLACE_MARKER_ICON_ANCHOR = [18, 32]; // XY coordinates *within* image of the geographical centre
const PLACE_MARKER_POPUP_ANCHOR = [0, -32]; // XY coordinates relative to icon anchor where popups arise

/**
 * Handle changes to the filters. We will update the map's colours.
 */
function updateTilesAndChart()
{
    updateClimateTileLayer(APP.climate_tile_layer);
    updateLocationClimate();
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
    let text = period_label + ' ' + measurement_label + ', ' + date_range;

    if (measurement !== 'potet') {
        text = 'Average ' + text;
    }

    tooltip.textContent = text;
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

    APP.location_marker = L.marker([0, 0]);

    APP.climates_of_places.icon = L.icon({
        iconUrl: PLACE_MARKER_ICON,
        iconSize: PLACE_MARKER_ICON_SIZE,
        iconAnchor: PLACE_MARKER_ICON_ANCHOR,
        popupAnchor: PLACE_MARKER_POPUP_ANCHOR,
        tooltipAnchor: PLACE_MARKER_POPUP_ANCHOR,
    });

    createBaseMapLayer();

    loadControlsHtml();
    loadChartHTML();

    APP.units = fetchPreferredUnits();
    updateUnitsButton(APP.units);


    const data_source_select = document.getElementById('data-source');
    const date_range_select = document.getElementById('date-range');
    const measurement_select = document.getElementById('measurement');
    const period_select = document.getElementById('period');

    /**
     * Populate the drop downs and render the climate map tiles.
     * Also show the location climate if there is a location in the
     * URL path.
     */
    populateDateRanges(date_range_select).then(function() {
        populateDataSources(data_source_select, date_range_select, measurement_select).then(function() {
            APP.climate_tile_layer = createClimateTileLayer().addTo(APP.climate_map);
            updateClimatesOfPlaces();
            highlightMeasurementButton(measurement_select.value);
            updateDescriptionTooltip(period_select.value, measurement_select.value, date_range_select.value);
            updateLegend(measurement_select.value, APP.units);
            goToURL(document.location.pathname); 
        });
    });

    /**
     * Handle changing the data source
     */
    function change_data_source() {
        updateTilesAndChart();
        updateClimatesOfPlaces();
        updateSSPButton(data_source_select.value);
    }

    data_source_select.onchange = function() {
        change_data_source();
        updateLastDataSource(data_source_select);
    };

    /**
     * Handle changing the date range dropdown.
     */
    handleDateRangeChanges();

    date_range_select.addEventListener('change', function() {
        populateDataSources(data_source_select, date_range_select, measurement_select).then(change_data_source).then(
            function() {
                if (!getLastDataSource(data_source_select)) {
                    updateLastDataSource(data_source_select);
                }
                updateDescriptionTooltip(period_select.value, measurement_select.value, date_range_select.value);
            }
        );
    });

    /**
     * Handle changing the measurement dropdown
     */
    handleMeasurementChanges();

    measurement_select.addEventListener('change', function() {
        populateDataSources(data_source_select, date_range_select, measurement_select).then(change_data_source).then(
            function() {
                updateDescriptionTooltip(period_select.value, measurement_select.value, date_range_select.value);
            }
        );
    });

    /**
     * Handle changing the period dropdown.
     */
    period_select.onchange = function() {
        updateClimateTileLayer(APP.climate_tile_layer);
        updateDescriptionTooltip(period_select.value, measurement_select.value, date_range_select.value);
        updateClimatesOfPlaces();
    };

    /**
     * Handle clicking at a location on the map.
     */
    APP.climate_map.on('click', function(e) {
        let lat = e.latlng.lat;
        let lon = e.latlng.lng;

        viewLocationClimate(lat, lon);
    });

    /**
     * Handle zooming and panning.
     */
    APP.climate_map.on('moveend', updateClimatesOfPlaces);

    /**
     * Handle search.
     */
    handleSearch();

    /**
     * Handle clicking the buttons on the side.
     */
    document.getElementById('filter-button').onclick = function() {
        this.classList.toggle('hamburger-close');
        const filters_div = document.getElementById('filter-container');
        filters_div.style.display = (filters_div.style.display == 'none') ? 'block' : 'none';
    };

    document.getElementById('ssp-button').onclick = function() {
        updateSSP(data_source_select.onchange);
    };

    handleUnits();

    document.getElementById('units-button').addEventListener('click', function() {
        updateClimateCharts(APP.data);

        const bounds = APP.climate_map.getBounds();
        setClimatesOfPlaces(APP.climates_of_places.places, bounds);
    });

    handleAbout();

    /**
     * Handle the back button.
     */
    window.onpopstate = function(e) {
        if (e.state) {
            goToPageState(e.state);
        }
    };
};
