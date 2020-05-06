-- Inserts data into tables
INSERT INTO units(code, name)
VALUES
    ('degC', '°C'),
    ('mm', 'Millimetres'),
    ('m', 'Metres');

INSERT INTO measurements(code, name)
VALUES
    ('tmin', 'Minimum temperature'),
    ('tmax', 'Maximum temperature'),
    ('tavg', 'Mean temperature'),
    ('precip', 'Total precipitation'),
    ('et', 'Actual Evapotranspiration'),
    ('potet', 'Potential Evapotranspiration'),
    ('elevation', 'Elevation');

-- Country no longer exists so it breaks a foreign key constraint.
INSERT INTO countries(code, name) VALUES ('YU', 'Federal Republic of Yugoslavia');
