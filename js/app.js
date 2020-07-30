/**
 * Houses a global APP object for sharing information
 * without having to pass it everywhere.
 *
 * Copyright (c) 2020 Carlos Torchia
 */

export const DEFAULT_PAGE_TITLE = 'Climate Map';

export const APP_URL = '/';

export default {
    charts: {},
    climates_of_places: {
        markers: null,
    },
};
