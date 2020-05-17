/**
 * Loads the UI control elements
 *
 * These controls allow the user to select the climate dataset they
 * want to look at.
 *
 * Copyright (c) 2020 Carlos Torchia
 */

import buttons_html from '../html/buttons.html';
import filters_html from '../html/filters.html';
import search_html from '../html/search.html';
import slider_html from '../html/slider.html';
import captions_html from '../html/captions.html';

/**
 * Loads control elements from HTML files, adding them to
 * the body element.
 */
export function loadControlsHtml()
{
    const template = document.createElement('template');

    template.innerHTML = [
        buttons_html,
        filters_html,
        search_html,
        slider_html,
        captions_html,
    ].join('\n');

    document.getElementsByTagName('body')[0].append(template.content);
}
