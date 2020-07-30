/**
 * Places AKA GeoNames
 *
 * This module contains functions to show place markers on the map
 * that the user can hover over to see climate details.
 *
 * In general, this module shall contain geoname specific functions
 * as geoname data is leveraged so much.
 *
 * If you're confused, think about the data produced by this module
 * like a "mashup" between the GeoNames database and the climate data.
 *
 * Copyright (c) 2020 Carlos Torchia
 */

import { getMeasurementLabel } from './measurements.js';
import { convertToUnits, getUnitLabel } from './units.js';
import { getPeriodLabel } from './periods.js';
import { viewLocationClimate } from './charts.js';
import { fetchClimatesOfPlaces } from './api.js';

import APP from './app.js';

/**
 * Returns the full pace name of the given geoname.
 * Particularly it appends the province or country to the name
 * so that the name has a degree of uniqueness that allows us
 * to look it up later (this will get specified in the URL).
 */
export function getPlaceName(geoname)
{
    if (geoname['province']) {
        return geoname['name'] + ', ' + geoname['province'];
    } else if (geoname['country']) {
        return geoname['name'] + ', ' + geoname['country'];
    }
}

/**
 * Updates the climates of populous places. This is used
 * to show one measurement as the user hovers over various
 * populated places like cities.
 */
export function updateClimatesOfPlaces()
{
    const bounds = APP.climate_map.getBounds();
    let restricted_bounds;

    if (bounds.getEast() - bounds.getWest() > 360) {
        const east_antimeridian = Math.round((bounds.getEast() + 180) / 360) * 360 - 180;
        const west_antimeridian = Math.round((bounds.getWest() + 180) / 360) * 360 - 180;

        restricted_bounds = L.latLngBounds(
            L.latLng(bounds.getSouth(), Math.max(bounds.getWest(), west_antimeridian + 0.1)),
            L.latLng(bounds.getNorth(), Math.min(bounds.getEast(), east_antimeridian - 0.1)),
        );
    } else {
        restricted_bounds = bounds;
    }

    const data_source_select = document.getElementById('data-source');
    const date_range_select = document.getElementById('date-range');
    const measurement_select = document.getElementById('measurement');
    const period_select = document.getElementById('period');

    return fetchClimatesOfPlaces(
        data_source_select.value,
        date_range_select.value,
        measurement_select.value,
        period_select.value,
        restricted_bounds
    ).then(function(places) {
        APP.climates_of_places.places = places;
        setClimatesOfPlaces(places, restricted_bounds);
    });
}

/**
 * Sets the current climates of places with the specified geonames.
 */
export function setClimatesOfPlaces(places, bounds)
{
    let active_markers = [];

    if (!APP.climates_of_places.markers) {
        APP.climates_of_places.markers = L.layerGroup();
        APP.climates_of_places.markers.addTo(APP.climate_map);
    } else {
        APP.climates_of_places.markers.clearLayers();
    }

    for (let i = 0; i <= places.length - 1; i++) {
        const geoname = places[i];
        const tooltip_text = climateOfPlaceTooltipText(geoname);

        if (tooltip_text) {
            const caption = document.createElement('div');

            caption.className = 'place-name-text';
            caption.textContent = geoname.name;

            APP.climates_of_places.markers[i] = L.marker([0, 0], {
                icon: L.divIcon({
                    html: caption,
                    className: 'place-name',
                }),
            }).addTo(APP.climates_of_places.markers);

            const marker = APP.climates_of_places.markers[i];

            const [lat, lon] = normalizeCoordinates(geoname.latitude, geoname.longitude, bounds);

            marker.setLatLng([lat, lon]);

            /**
             * The places are sorted in order of descending population,
             * therefore we hide the current marker in order to show the
             * more populated place instead.
             *
             * The marker has to already be added to the map in order to know
             * whether it overlaps because it does not have a width and
             * height until it is displayed.
             */
            if (markerOverlapsExisting(marker, active_markers)) {
                marker.setOpacity(0);
                marker.remove();
            } else {
                active_markers.push(marker);

                marker.bindTooltip(tooltip_text, {
                    direction: 'center',
                    className: 'place-tooltip',
                });

                marker.on('click', function() {
                    viewPlaceClimate(geoname);
                });

                /**
                 * Center the text on the location.
                 * Element display must be inline-block for this to work.
                 */
                caption.style.marginLeft = '-' + (caption.clientWidth / 2) + 'px';
                caption.style.marginTop = '-' + (caption.clientHeight / 2) + 'px';
            }
        }
    }
}

/**
 * Normalizes latitude and longitude to the specified
 * bounds.
 *
 * If the coordinates are outside the bounds, the equivalent
 * coordinate within the bounds will be used instead.
 *
 * For example, if the longitude bounds are -180 to 180,
 * then longitude 243 would get converted to -117.
 */
function normalizeCoordinates(lat, lon, bounds)
{
    const west_revolutions = Math.ceil((bounds.getWest() + 180) / 360);
    const east_revolutions = Math.floor((bounds.getEast() + 180) / 360);

    const normalized_west_bound = ((bounds.getWest() + 180) % 360 + 360) % 360 - 180;
    const normalized_east_bound = ((bounds.getEast() + 180) % 360 + 360) % 360 - 180;

    if (lon >= normalized_west_bound) {
        lon += (west_revolutions - 1) * 360;
    } else if (lon < normalized_east_bound) {
        lon += east_revolutions * 360;
    } else {
        lon += west_revolutions * 360;
    }

    return [lat, lon];
}

/**
 * Returns the text containing climate info of a place the
 * user has hovered over.
 *
 * Returns null if measurement data is not available for this geoname.
 */
function climateOfPlaceTooltipText(geoname)
{
    const date_range = document.getElementById('date-range').value;
    const period = document.getElementById('period').value;
    const measurement = document.getElementById('measurement').value;

    const measurement_label = getMeasurementLabel(measurement);
    const period_label = getPeriodLabel(period);

    const name = geoname.name;

    if (geoname[measurement] !== undefined) {
        let [value, units] = convertToUnits(geoname[measurement], APP.units);

        if ((units == 'mm' || units == 'in') && period === 'year') {
            value *= 12;
        }

        let text = '<b>' + name + '</b>';
        text += '<br>\nAverage ' + measurement_label + ' ' + period_label + ': ';
        text += Math.round(value * 10) / 10 + ' ' + getUnitLabel(units);
        if (units == 'mm' && period !== 'year') {
            text += '/month';
        }
        text += '<br>\n(' + date_range + ')';
        text += '<br>\n<i>Click for more details.</i>'

        return text;
    } else {
        return null;
    }
}

/**
 * Displays the climate charts for the place that
 * the user is hovering over with their mouse.
 * Called when the user clicks on a marker.
 */
function viewPlaceClimate(geoname)
{
    const lat = geoname.latitude;
    const lon = geoname.longitude;
    const name = getPlaceName(geoname);

    viewLocationClimate(lat, lon, name);
}

/**
 * Determines if the specified map marker overlaps any existing
 * map markers.
 *
 * We need to know this because the text in the DivIcon map markers
 * can overlap and this looks awful.
 *
 * @param Marker marker
 * @param Marker[] existing_markers
 * @return true if marker overlaps with existing marker, false otherwise
 */
function markerOverlapsExisting(marker, existing_markers)
{
    for (let i = 0; i <= existing_markers.length - 1; i++) {
        const existing_marker = existing_markers[i];

        if (existing_marker !== marker) {
            if (APP.climate_map.hasLayer(existing_marker)) {
                if (markersOverlap(marker, existing_marker)) {
                    return true;
                }
            }
        }
    }

    return false;
}

/**
 * Determines if the specified markers overlap.
 *
 * @param Marker new_marker
 * @param Marker existing_marker
 *
 * @return boolean
 */
function markersOverlap(new_marker, existing_marker)
{
    if (new_marker.getElement() === undefined) {
        throw Error('New marker must already be on the map.');
    }

    if (existing_marker.getElement() === undefined) {
        throw Error('Existing marker must already be on the map.');
    }

    const new_child = new_marker.getElement().children[0];
    const existing_child = existing_marker.getElement().children[0];

    if (!new_child.classList.contains('place-name-text')) {
        throw Error('Expected first child of the new "place-name" div to have the "place-name-text" class.');
    }

    if (!existing_child.classList.contains('place-name-text')) {
        throw Error('Expected first child of the existing "place-name" div to have the "place-name-text" class.');
    }

    const new_width = new_child.clientWidth;
    const new_height = new_child.clientHeight;

    if (!new_width) {
        throw Error('Cannot determine marker width. Is the place-name-text child not inline-block?');
    }

    if (!new_height) {
        throw Error('Cannot determine marker height. Is the place-name-text child not inline-block?');
    }

    const existing_width = existing_child.clientWidth;
    const existing_height = existing_child.clientHeight;

    if (!existing_width) {
        throw Error('Cannot determine existing marker width. Is the place-name-text child not inline-block?');
    }

    if (!existing_height) {
        throw Error('Cannot determine existing marker height. Is the place-name-text child not inline-block?');
    }

    const new_point = APP.climate_map.latLngToLayerPoint(new_marker.getLatLng());
    const existing_point = APP.climate_map.latLngToLayerPoint(existing_marker.getLatLng());

    const new_left = new_point.x - new_width / 2;
    const new_right = new_point.x + new_width / 2;

    const existing_left = existing_point.x - new_width / 2;
    const existing_right = existing_point.x + new_width / 2;

    const new_top = new_point.y - new_height / 2;
    const new_bottom = new_point.y + new_height / 2;

    const existing_top = existing_point.y - existing_height / 2;
    const existing_bottom = existing_point.y + existing_height / 2;

    if (new_left > existing_right) {
        return false;
    }

    if (new_right < existing_left) {
        return false;
    }

    if (new_top > existing_bottom) {
        return false;
    }

    if (new_bottom < existing_top) {
        return false;
    }

    return true;
}
