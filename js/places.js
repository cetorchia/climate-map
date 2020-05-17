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
    const restricted_bounds = L.latLngBounds(
        bounds.getSouthWest(),
        L.latLng(bounds.getNorth(), Math.min(bounds.getEast(), bounds.getWest() + 360)),
    );

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
        setClimatesOfPlaces(places, bounds);
    });
}

/**
 * Sets the current climates of places with the specified geonames.
 */
export function setClimatesOfPlaces(places, bounds)
{
    const west_revolutions = Math.ceil((bounds.getWest() + 180) / 360);
    const east_revolutions = Math.floor((bounds.getEast() + 180) / 360);

    for (let i = 0; i <= places.length - 1; i++) {
        const geoname = places[i];
        const tooltip_text = climateOfPlaceTooltipText(geoname);

        if (APP.climates_of_places.markers[i] !== undefined) {
            APP.climates_of_places.markers[i].remove();
        }

        if (tooltip_text) {
            APP.climates_of_places.markers[i] = L.marker([0, 0], {
                icon: APP.climates_of_places.icon,
            }).addTo(APP.climate_map);

            const marker = APP.climates_of_places.markers[i];
            const lat = geoname.latitude;
            let lon = geoname.longitude;

            const normalized_west_bound = ((bounds.getWest() + 180) % 360 + 360) % 360 - 180;
            const normalized_east_bound = ((bounds.getEast() + 180) % 360 + 360) % 360 - 180;

            if (lon >= normalized_west_bound) {
                lon += (west_revolutions - 1) * 360;
            } else if (lon < normalized_east_bound) {
                lon += east_revolutions * 360;
            } else {
                lon += west_revolutions * 360;
            }

            marker.setLatLng([lat, lon]);
            marker.bindTooltip(tooltip_text, {
                direction: 'center',
            });

            marker.on('click', function() {
                viewPlaceClimate(geoname);
            });
        }
    }
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
