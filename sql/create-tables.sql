-- Creates tables for the climate map database

CREATE TABLE units(
    id SERIAL PRIMARY KEY,
    code VARCHAR(32) UNIQUE,
    name VARCHAR(64)
);

CREATE TABLE measurements(
    id SERIAL PRIMARY KEY,
    code VARCHAR(32) UNIQUE,
    name VARCHAR(64)
);

CREATE TABLE data_sources(
    id SERIAL PRIMARY KEY,
    code VARCHAR(32) UNIQUE,
    name VARCHAR(64),
    organisation VARCHAR(64),
    author VARCHAR(64),
    url VARCHAR(2000)
);

CREATE TABLE datasets(
    id SERIAL PRIMARY KEY,
    data_source_id INTEGER REFERENCES data_sources(id),
    start_date DATE,
    end_date DATE
);

-- SRID 4326 (WGS 84) basically goes from longitude -180 to 180 and latitude -90 to 90.
-- This must be the same as the coordinate ranges used by the application.
CREATE TABLE data_points(
    id SERIAL PRIMARY KEY,
    dataset_id INTEGER REFERENCES datasets(id),
    location GEOGRAPHY(POINT, 4326)
);

CREATE INDEX ON data_points USING GIST(location);

CREATE TABLE monthly_normals(
    id SERIAL PRIMARY KEY,
    data_point_id INTEGER REFERENCES data_points(id),
    measurement_id INTEGER REFERENCES measurements(id),
    unit_id INTEGER REFERENCES units(id),
    month INTEGER,
    value FLOAT
);
