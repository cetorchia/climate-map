-- Sets up the relational database
-- with postgis.

-- First create the databse
CREATE DATABASE climate_map;
\c climate_map

CREATE LANGUAGE plpgsql;

-- Create the main user who will access the database
CREATE USER climate_map;
ALTER USER climate_map WITH PASSWORD 'a_mKWpF60)'; -- Change this!
GRANT ALL ON DATABASE climate_map TO climate_map;

-- Add the postgis extension
CREATE EXTENSION postgis;
CREATE EXTENSION postgis_topology;
