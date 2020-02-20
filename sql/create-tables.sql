-- Creates tables for the climate map database

CREATE TABLE units(
    id INTEGER AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(32) NOT NULL UNIQUE,
    name VARCHAR(64) NOT NULL
);

CREATE TABLE measurements(
    id INTEGER AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(32) NOT NULL UNIQUE,
    name VARCHAR(64) NOT NULL
);

CREATE TABLE data_sources(
    id INTEGER AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(32) NOT NULL UNIQUE,
    name VARCHAR(128) NOT NULL,
    organisation VARCHAR(64),
    author VARCHAR(128),
    year VARCHAR(64),
    url VARCHAR(2000) NOT NULL,
    max_zoom_level SMALLINT NOT NULL DEFAULT 5,
    baseline BOOLEAN NOT NULL DEFAULT FALSE,
    active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE datasets(
    id INTEGER AUTO_INCREMENT PRIMARY KEY,
    data_source_id INTEGER NOT NULL REFERENCES data_sources(id),
    measurement_id INTEGER NOT NULL REFERENCES measurements(id),
    unit_id INTEGER NOT NULL REFERENCES units(id),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    lat_start DOUBLE(12, 10) NOT NULL,
    lat_delta DOUBLE(12, 10) NOT NULL,
    lon_start DOUBLE(13, 10) NOT NULL,
    lon_delta DOUBLE(13, 10) NOT NULL,
    fill_value INTEGER NOT NULL,
    filename VARCHAR(128) NOT NULL,
    lat_filename VARCHAR(128) NOT NULL,
    lon_filename VARCHAR(128) NOT NULL,
    calibrated BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE(data_source_id, measurement_id, unit_id, start_date, end_date, calibrated)
);

CREATE TABLE search_queue(
    id INTEGER AUTO_INCREMENT PRIMARY KEY,
    timestamp DOUBLE(16, 6) NOT NULL,
    UNIQUE(timestamp)
);
