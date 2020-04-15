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
    ('precip', 'Total precipitation'),
    ('et', 'Actual Evapotranspiration'),
    ('potet', 'Potential Evapotranspiration');

INSERT INTO data_sources(code, name, organisation, author, url, year, baseline, active)
    ('udel', 'University of Delaware Air Temperature and Precipitation', 'University of Delaware (via NOAA)', 'C. J. and K. Matsuura', 'https://www.esrl.noaa.gov/psd/data/gridded/data.UDel_AirT_Precip.html', '2001', true, false),
    ('worldclim', 'WorldClim 1.4, 2.0', 'WorldClim.org', 'Fick, S.E. and R.J. Hijmans', 'http://worldclim.org/', '2005, 2017', true, false),
    ('TerraClimate', 'TerraClimate', 'TerraClimate', 'Abatzoglou, J.T., S.Z. Dobrowski, S.A. Parks, K.C. Hegewisch', 'https://doi.org/10.1038/sdata.2017.191', '2018', true, true);

INSERT INTO data_sources(code, name, organisation, author, url, year, active)
VALUES
    ('CNRM-CM6-1-HR.historical', 'CNRM-CM6-1-HR historical', 'CNRM-CERFACS', 'Voldoire, Aurore', 'http://doi.org/10.22033/ESGF/CMIP6.4067', '2019', false),
    ('CNRM-CM6-1-HR.ssp245', 'CNRM-CM6 middle of the road', 'CNRM-CERFACS', 'Voldoire, Aurore', 'http://doi.org/10.22033/ESGF/CMIP6.4190', '2019', true),
    ('CNRM-CM6-1-HR.ssp585', 'CNRM-CM6 fossil fueled development', 'CNRM-CERFACS', 'Voldoire, Aurore', 'http://doi.org/10.22033/ESGF/CMIP6.4225', '2019', true),
    ('CanESM5-CanOE.historical', 'CanESM5-CanOE historical', 'CCCma', 'Swart, Neil Cameron; Cole, Jason N.S.; Kharin, Viatcheslav V. et al.', 'http://doi.org/10.22033/ESGF/CMIP6.10260', '2019', false),
    ('CanESM5-CanOE.ssp245', 'CanESM5 middle of the road', 'CCCma', 'Swart, Neil Cameron; Cole, Jason N.S.; Kharin, Viatcheslav V. et al.', 'http://doi.org/10.22033/ESGF/CMIP6.10270', '2019', false),
    ('CanESM5-CanOE.ssp585', 'CanESM5 fossil fueled development', 'CCCma', 'Swart, Neil Cameron; Cole, Jason N.S.; Kharin, Viatcheslav V. et al.', 'http://doi.org/10.22033/ESGF/CMIP6.10276', '2019', false),
    ('CanESM5.historical', 'CanESM5 historical', 'CCCma', 'Swart, Neil Cameron; Cole, Jason N.S.; Kharin, Viatcheslav V. et al.', 'http://doi.org/10.22033/ESGF/CMIP6.3610', '2019', true),
    ('CanESM5.ssp245', 'CanESM5 middle of the road', 'CCCma', 'Swart, Neil Cameron; Cole, Jason N.S.; Kharin, Viatcheslav V. et al.', 'http://doi.org/10.22033/ESGF/CMIP6.3685', '2019', true),
    ('CanESM5.ssp585', 'CanESM5 fossil fueled development', 'CCCma', 'Swart, Neil Cameron; Cole, Jason N.S.; Kharin, Viatcheslav V. et al.', 'http://doi.org/10.22033/ESGF/CMIP6.3696', '2019', true),
    ('MRI-AGCM3-2-S.highresSST-future', 'MRI-AGCM3-2 fossil fueled development', 'MRI', 'Mizuta, Ryo; Yoshimura, Hiromasa; Ose, Tomoaki et al.', 'http://doi.org/10.22033/ESGF/CMIP6.6740', '2019', false),
    ('MRI-ESM2-0.historical', 'MRI-ESM2 historical', 'MRI', 'Yukimoto, Seiji; Koshiro, Tsuyoshi; Kawai, Hideaki et al.', 'http://doi.org/10.22033/ESGF/CMIP6.6842', '2019', true),
    ('MRI-ESM2-0.ssp245', 'MRI-ESM2 middle of the road', 'MRI', 'Yukimoto, Seiji; Koshiro, Tsuyoshi; Kawai, Hideaki et al.', 'http://doi.org/10.22033/ESGF/CMIP6.6910', '2019', true),
    ('MRI-ESM2-0.ssp585', 'MRI-ESM2 fossil fueled development', 'MRI', 'Yukimoto, Seiji; Koshiro, Tsuyoshi; Kawai, Hideaki et al.', 'http://doi.org/10.22033/ESGF/CMIP6.6929', '2019', true),
    ('GFDL-ESM4.ssp245', 'GFDL-ESM4 middle of the road', 'NOAA', 'John, Jasmin G; Blanton, Chris; McHugh, Colleen et al.', 'http://doi.org/10.22033/ESGF/CMIP6.8686', '2018', true),
    ('GFDL-ESM4.ssp585', 'GFDL-ESM4 fossil fueled development', 'NOAA', 'John, Jasmin G; Blanton, Chris; McHugh, Colleen et al.', 'http://doi.org/10.22033/ESGF/CMIP6.8686', '2018', true);

-- Country no longer exists so it breaks a foreign key constraint.
INSERT INTO countries(code, name) VALUES ('YU', 'Federal Republic of Yugoslavia');
