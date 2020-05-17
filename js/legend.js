/**
 * Displays the legend to the user.
 *
 * Copyright (c) 2020 Carlos Torchia
 */

import legend_tavg_metric from '../images/legend-tavg-metric.png';
import legend_tavg_imperial from '../images/legend-tavg-imperial.png';
import legend_precip_metric from '../images/legend-precip-metric.png';
import legend_precip_imperial from '../images/legend-precip-imperial.png';
import legend_potet_metric from '../images/legend-potet-metric.png';
import legend_potet_imperial from '../images/legend-potet-imperial.png';

const LEGEND_URL = {
    'tavg': {
        'metric': legend_tavg_metric,
        'imperial': legend_tavg_imperial,
    },
    'precip': {
        'metric': legend_precip_metric,
        'imperial': legend_precip_imperial,
    },
    'potet': {
        'metric': legend_potet_metric,
        'imperial': legend_potet_imperial,
    },
};

/**
 * Update the legend for the specified measurement.
 */
export function updateLegend(measurement, units)
{
    const legend_img = document.createElement('img');

    legend_img.src = LEGEND_URL[measurement][units];

    const legend_div = document.getElementById('legend');

    legend_div.innerHTML = '';
    legend_div.append(legend_img);
}
