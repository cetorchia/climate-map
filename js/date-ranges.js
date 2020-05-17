/**
 * Main climate map javascript.
 *
 * Copyright (c) 2020 Carlos Torchia
 */

import { fetchDateRanges } from './api.js';
import { fireEvent } from './util.js';

/**
 * Populates the date ranges from valid datasets for this data source.
 */
export async function populateDateRanges(date_range_select)
{
    const date_ranges = await fetchDateRanges();

    /* Remove all existing options. */
    date_range_select.innerHTML = '';

    /* Add each data source. */
    for (let i = 0; i <= date_ranges.length - 1; i++) {
        let date_range = date_ranges[i];
        let option = document.createElement('option');

        option.text = date_range;
        option.value = date_range;

        date_range_select.add(option);
    }

    populateDateRangeSlider(date_ranges, date_range_select.selectedIndex);
}

/**
 * Populates the data list for the date range slider.
 */
function populateDateRangeSlider(date_ranges, selected_index)
{
    const date_range_slider = document.getElementById('date-range-slider');

    date_range_slider.min = 0;
    date_range_slider.max = date_ranges.length - 1;
    date_range_slider.value = selected_index;
}

/**
 * Updates the tooltip below the date range slider to show
 * the selected date range.
 */
function updateDateRangeSliderTooltip()
{
    const selected_index = document.getElementById('date-range-slider').value;
    const date_range = document.getElementById('date-range').options[selected_index].value;
    const tooltip = document.getElementById('date-range-slider-tooltip');
    tooltip.style.display = 'block';
    tooltip.innerHTML = date_range;
}

/**
 * Hides the tooltip below the date range
 */
function hideDateRangeSliderTooltip()
{
    const tooltip = document.getElementById('date-range-slider-tooltip');
    tooltip.style.display = 'none';
}

/**
 * Sets up event listeners to the date range controls.
 */
export function handleDateRangeChanges()
{
    const date_range_select = document.getElementById('date-range');
    const date_range_slider = document.getElementById('date-range-slider');

    date_range_select.addEventListener('change', function() {
        date_range_slider.value = date_range_select.selectedIndex;
    });

    /**
     * Handle sliding the date range slider.
     */
    date_range_slider.addEventListener('change', function(e) {
        date_range_select.selectedIndex = e.target.value;
        fireEvent(date_range_select, 'change');
        hideDateRangeSliderTooltip();
    });

    date_range_slider.onmousedown = updateDateRangeSliderTooltip;
    date_range_slider.onmouseup = hideDateRangeSliderTooltip;
    date_range_slider.oninput = updateDateRangeSliderTooltip;
    date_range_slider.onkeydown = updateDateRangeSliderTooltip;
}
