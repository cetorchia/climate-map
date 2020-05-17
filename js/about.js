/**
 * Functions for displaying the about screen.
 *
 * Copyright (c) 2020 Carlos Torchia
 */

import CONFIG from '../config/config.json';

import about_html from '../html/about.html';

/**
 * Returns the email address of the specified contact.
 */
function getContact(contact_name)
{
    return CONFIG.contact[contact_name].username + '@' + CONFIG.contact[contact_name].domain;
}

/**
 * Loads the About HTML.
 */
async function loadAboutHtml()
{
    const template = document.createElement('template');
    template.innerHTML = about_html;
    document.getElementsByTagName('body')[0].append(template.content);

    displaySupportContact();
}

/**
 * Display the support contact.
 */
function displaySupportContact()
{
    const support_contact = getContact('support');
    document.getElementById('support-contact').innerHTML =
        '<a href="mailto:' + support_contact + '">' + support_contact + '</a>';
}

/**
 * Handle clicking the about button.
 */
export function handleAbout()
{
    loadAboutHtml();

    document.getElementById('about-button').onclick = function() {
        const about_div = document.getElementById('about');
        about_div.style.display = (about_div.style.display == 'none') ? 'block' : 'none';
    };

    document.getElementById('close-about').onclick = function() {
        const about_div = document.getElementById('about');
        about_div.style.display = 'none';
    };
}
