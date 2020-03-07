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
    data_source_id INTEGER NOT NULL,
    measurement_id INTEGER NOT NULL,
    unit_id INTEGER NOT NULL,
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
    UNIQUE(data_source_id, measurement_id, unit_id, start_date, end_date, calibrated),
    FOREIGN KEY (data_source_id) REFERENCES data_sources(id),
    FOREIGN KEY (measurement_id) REFERENCES measurements(id),
    FOREIGN KEY (unit_id) REFERENCES units(id)
);

CREATE TABLE countries(
    code CHAR(2) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    geonameid INTEGER
);

CREATE TABLE provinces(
    province_code VARCHAR(8),
    name VARCHAR(100) NOT NULL,
    country CHAR(2) NOT NULL,
    geonameid INTEGER,
    PRIMARY KEY(province_code, country),
    FOREIGN KEY (country) REFERENCES countries(code)
);

CREATE TABLE geonames(
    geonameid INTEGER PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    latitude DOUBLE(12, 10) NOT NULL,
    longitude DOUBLE(13, 10) NOT NULL,
    country CHAR(2),
    province VARCHAR(8),
    population BIGINT,
    elevation INTEGER,
    FOREIGN KEY (country) REFERENCES countries(code),
    FOREIGN KEY (province) REFERENCES provinces(province_code)
);

CREATE INDEX name ON geonames(name);
CREATE INDEX population_name ON geonames(population, name);

CREATE TABLE alternate_names(
    id INTEGER PRIMARY KEY,
    geonameid INTEGER NOT NULL,
    lang VARCHAR(5) NOT NULL,
    alternate_name VARCHAR(400) NOT NULL,
    preferred BOOLEAN NOT NULL,
    abbrev BOOLEAN NOT NULL,
    FOREIGN KEY (geonameid) REFERENCES geonames(geonameid)
);

CREATE INDEX alternate_name ON alternate_names(alternate_name);
