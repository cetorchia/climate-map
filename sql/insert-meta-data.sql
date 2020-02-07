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
    ('CanESM5-CanOE.historical', 'CanESM5-CanOE historical', 'CCCma', 'Swart, Neil Cameron; Cole, Jason N.S.; Kharin, Viatcheslav V. et al.', 'http://doi.org/10.22033/ESGF/CMIP6.10260', '2019'),
    ('CNRM-CM6-1-HR.historical', 'CNRM-CM6-1-HR historical', 'CRNM-CERFACS', 'Voldoire, Aurore', 'http://doi.org/10.22033/ESGF/CMIP6.4067', '2019'),
    ('udel', 'University of Delaware Air Temperature and Precipitation', 'University of Delaware (via NOAA)', 'C. J. and K. Matsuura', 'https://www.esrl.noaa.gov/psd/data/gridded/data.UDel_AirT_Precip.html', '2001'),
    ('TerraClimate', 'TerraClimate', 'TerraClimate', 'Abatzoglou, J.T., S.Z. Dobrowski, S.A. Parks, K.C. Hegewisch', 'https://doi.org/10.1038/sdata.2017.191', '2018');
