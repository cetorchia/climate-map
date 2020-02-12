-- Sets up the relational database

-- First create the databse
CREATE DATABASE climate_map;
USE climate_map;

-- Create the main user who will access the database
CREATE USER climate_map;
SET PASSWORD FOR climate_map = password('a_mKWpF60'); -- Change this!
GRANT ALL ON climate_map.* TO 'climate_map'@'%';
