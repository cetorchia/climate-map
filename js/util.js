/**
 * Miscellaneous functions that do not have to 
 * do with this project directly.
 *
 * This generally will include functions that must be
 * implemented in different ways depending on the browser.
 */

/**
 * Fires the specified event on a specified element.
 *
 * e.g. fireEvent(ok_button, 'click')
 *
 * Courtesy https://stackoverflow.com/a/2490876/5798510
 */
export function fireEvent(element, type)
{
    let event; // The custom event that will be created

    if(document.createEvent){
        /* Most browsers */
        event = document.createEvent("HTMLEvents");
        event.initEvent(type, true, true);
        event.eventName = type;
        element.dispatchEvent(event);
    } else {
        /* For IE8 compatibility */
        event = document.createEventObject();
        event.eventName = type;
        event.eventType = type;
        element.fireEvent("on" + event.eventType, event);
    }
}
