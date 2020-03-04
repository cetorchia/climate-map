-- Sets up the relational database

-- First create the databse
CREATE DATABASE climate_map CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE climate_map;

-- Create the main user who will access the database
CREATE USER climate_map;
SET PASSWORD FOR climate_map = password('a_mKWpF60'); -- Change this!
GRANT ALL ON climate_map.* TO 'climate_map'@'%';
