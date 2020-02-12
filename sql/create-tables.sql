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
    active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE datasets(
    id INTEGER AUTO_INCREMENT PRIMARY KEY,
    data_source_id INTEGER NOT NULL REFERENCES data_sources(id),
    measurement_id INTEGER NOT NULL REFERENCES measurements(id),
    unit_id INTEGER NOT NULL REFERENCES units(id),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    lat_start FLOAT NOT NULL,
    lat_delta FLOAT NOT NULL,
    lon_start FLOAT NOT NULL,
    lon_delta FLOAT NOT NULL,
    filename VARCHAR(128) NOT NULL,
    lat_filename VARCHAR(128) NOT NULL,
    lon_filename VARCHAR(128) NOT NULL,
    UNIQUE(data_source_id, measurement_id, unit_id, start_date, end_date)
);

CREATE TABLE search_queue(
    id INTEGER AUTO_INCREMENT PRIMARY KEY,
    timestamp FLOAT NOT NULL,
    UNIQUE(timestamp)
);
