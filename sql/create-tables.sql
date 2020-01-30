-- Creates tables for the climate map database

CREATE TABLE units(
    id SERIAL PRIMARY KEY,
    code VARCHAR(32) NOT NULL UNIQUE,
    name VARCHAR(64) NOT NULL
);

CREATE TABLE measurements(
    id SERIAL PRIMARY KEY,
    code VARCHAR(32) NOT NULL UNIQUE,
    name VARCHAR(64) NOT NULL
);

CREATE TABLE data_sources(
    id SERIAL PRIMARY KEY,
    code VARCHAR(32) NOT NULL UNIQUE,
    name VARCHAR(128) NOT NULL,
    organisation VARCHAR(64),
    author VARCHAR(128),
    year, VARCHAR(64),
    url VARCHAR(2000) NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE datasets(
    id SERIAL PRIMARY KEY,
    data_source_id INTEGER NOT NULL REFERENCES data_sources(id),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    delta FLOAT
);

-- SRID 4326 (WGS 84) basically goes from longitude -180 to 180 and latitude -90 to 90.
-- This must be the same as the coordinate ranges used by the application.
CREATE TABLE data_points(
    id SERIAL PRIMARY KEY,
    dataset_id INTEGER NOT NULL REFERENCES datasets(id),
    location GEOMETRY NOT NULL,
    UNIQUE(dataset_id, location)
);

CREATE INDEX ON data_points USING GIST(location);

CREATE TABLE monthly_normals(
    id SERIAL PRIMARY KEY,
    data_point_id INTEGER NOT NULL REFERENCES data_points(id),
    measurement_id INTEGER NOT NULL REFERENCES measurements(id),
    unit_id INTEGER NOT NULL REFERENCES units(id),
    month INTEGER NOT NULL,
    value FLOAT NOT NULL,
    UNIQUE(data_point_id, measurement_id, month)
);
