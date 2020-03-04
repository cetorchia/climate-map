-- Creates tables for the climate map database

CREATE TABLE units(
    id INTEGER AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(32) NOT NULL UNIQUE,
    name VARCHAR(64) NOT NULL
) CHARACTER SET=utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE measurements(
    id INTEGER AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(32) NOT NULL UNIQUE,
    name VARCHAR(64) NOT NULL
) CHARACTER SET=utf8mb4 COLLATE utf8mb4_unicode_ci;

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
) CHARACTER SET=utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE datasets(
    id INTEGER AUTO_INCREMENT PRIMARY KEY,
    data_source_id INTEGER NOT NULL REFERENCES data_sources(id),
    measurement_id INTEGER NOT NULL REFERENCES measurements(id),
    unit_id INTEGER NOT NULL REFERENCES units(id),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    lat_start DECIMAL(12, 10) NOT NULL,
    lat_delta DECIMAL(12, 10) NOT NULL,
    lon_start DECIMAL(13, 10) NOT NULL,
    lon_delta DECIMAL(13, 10) NOT NULL,
    fill_value INTEGER NOT NULL,
    filename VARCHAR(128) NOT NULL,
    lat_filename VARCHAR(128) NOT NULL,
    lon_filename VARCHAR(128) NOT NULL,
    calibrated BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE(data_source_id, measurement_id, unit_id, start_date, end_date, calibrated)
) CHARACTER SET=utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE search_queue(
    id INTEGER AUTO_INCREMENT PRIMARY KEY,
    timestamp DECIMAL(16, 6) NOT NULL,
    UNIQUE(timestamp)
) CHARACTER SET=utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE geonames(
    geonameid INTEGER PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    alternatenames VARCHAR(1000) NOT NULL,
    latitude DECIMAL(12, 10) NOT NULL,
    longitude DECIMAL(13, 10) NOT NULL,
    country CHAR(2),
    population INTEGER,
    elevation INTEGER
) CHARACTER SET=utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE INDEX name ON geonames(name);
CREATE FULLTEXT INDEX alternatenames ON geonames(alternatenames);
