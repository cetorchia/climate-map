/**
 * Error handling
 *
 * Copyright (c) 2020 Carlos Torchia
 */

/**
 * Default error messages.
 */
const DEFAULT_ERROR_MESSAGE = 'An error occurred. Please try again later.';

/**
 * Strips tags from input.
 * See https://stackoverflow.com/a/5499821
 */
function escapeHtmlTags(str)
{
    const tags_to_replace = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
    };

    function replace_tag(tag) {
        return tags_to_replace[tag] || tag;
    }

    return str.replace(/[&<>]/g, replace_tag);
}

/**
 * Displays an error message on the screen.
 */
export function showError(message)
{
    if (message === undefined) {
        message = DEFAULT_ERROR_MESSAGE;
    }

    let error_container = document.getElementById('error-container');

    if (error_container) {
        error_container.style.display = 'block';
        const message_span = document.getElementById('error-span');
        message_span.textContent = escapeHtmlTags(message);
    } else {
        error_container = document.createElement('div');
        error_container.setAttribute('id', 'error-container');
        error_container.setAttribute('class', 'map-window');

        const message_span = document.createElement('span');
        message_span.setAttribute('id', 'error-span');
        message_span.textContent = escapeHtmlTags(message);
        error_container.append(message_span);

        const error_close = document.createElement('div');
        error_close.setAttribute('id', 'error-container-close');
        error_close.setAttribute('class', 'container-close');
        error_close.textContent = 'X';
        error_close.onclick = hideError;
        error_container.append(error_close);

        const body = document.getElementsByTagName('body')[0];
        body.append(error_container);
    }

    return error_container;
}

/**
 * Hides the error message.
 */
export function hideError()
{
    const error_container = document.getElementById('error-container');

    if (error_container !== null) {
        error_container.style.display = 'none';
    }
}
