-- Inserts data into tables

INSERT INTO units(code, name)
VALUES
    ('degC', '°C'),
    ('mm', 'Millimetres');

INSERT INTO measurements(code, name)
VALUES
    ('tmin', 'Minimum temperature'),
    ('tmax', 'Maximum temperature'),
    ('tavg', 'Mean temperature'),
    ('precip', 'Total precipitation');

INSERT INTO data_sources(code, name, organisation, author, url, year)
VALUES
    ('worldclim', 'WorldClim 1.4, 2.0', 'WorldClim.org', 'Fick, S.E. and R.J. Hijmans', 'http://worldclim.org/', '2005, 2017'),
    ('udel', 'University of Delaware Air Temperature and Precipitation', 'University of Delaware (via NOAA)', 'C. J. and K. Matsuura', 'https://www.esrl.noaa.gov/psd/data/gridded/data.UDel_AirT_Precip.html', '2001');
