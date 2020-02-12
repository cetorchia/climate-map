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

INSERT INTO data_sources(code, name, organisation, author, url, year, active)
VALUES
    ('worldclim', 'WorldClim 1.4, 2.0', 'WorldClim.org', 'Fick, S.E. and R.J. Hijmans', 'http://worldclim.org/', '2005, 2017', false),
    ('CanESM5-CanOE.historical', 'CanESM5-CanOE historical', 'CCCma', 'Swart, Neil Cameron; Cole, Jason N.S.; Kharin, Viatcheslav V. et al.', 'http://doi.org/10.22033/ESGF/CMIP6.10260', '2019', false),
    ('CNRM-CM6-1-HR.historical', 'CNRM-CM6-1-HR historical', 'CNRM-CERFACS', 'Voldoire, Aurore', 'http://doi.org/10.22033/ESGF/CMIP6.4067', '2019', false),
    ('udel', 'University of Delaware Air Temperature and Precipitation', 'University of Delaware (via NOAA)', 'C. J. and K. Matsuura', 'https://www.esrl.noaa.gov/psd/data/gridded/data.UDel_AirT_Precip.html', '2001', false),
    ('TerraClimate', 'TerraClimate', 'TerraClimate', 'Abatzoglou, J.T., S.Z. Dobrowski, S.A. Parks, K.C. Hegewisch', 'https://doi.org/10.1038/sdata.2017.191', '2018', true),
    ('CNRM-CM6-1-HR.ssp245', 'CNRM-CM6 middle of the road', 'CNRM-CERFACS', 'Voldoire, Aurore', 'http://doi.org/10.22033/ESGF/CMIP6.4190', '2019', true),
    ('CanESM5-CanOE.ssp245', 'CanESM5 middle of the road', 'CCCma', 'Swart, Neil Cameron; Cole, Jason N.S.; Kharin, Viatcheslav V. et al.', 'http://doi.org/10.22033/ESGF/CMIP6.10270', '2019', true),
    ('CNRM-CM6-1-HR.ssp585', 'CNRM-CM6 fossil fueled development', 'CNRM-CERFACS', 'Voldoire, Aurore', 'http://doi.org/10.22033/ESGF/CMIP6.4225', '2019', true),
    ('CanESM5-CanOE.ssp585', 'CanESM5 fossil fueled development', 'CCCma', 'Swart, Neil Cameron; Cole, Jason N.S.; Kharin, Viatcheslav V. et al.', 'http://doi.org/10.22033/ESGF/CMIP6.10276', '2019', true);
