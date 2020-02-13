# Climate map

(c) 2020 Carlos Torchia

# Installation

To install the climate map, first use npm to build the javascript.

```
npm run build
```

Install the following Ubuntu packages, or equivalent:

* python3-numpy
* python3-netcdf4
* python3-gdal
* python3-matplotlib
* python3-opencv
* python3-flask
* python3-mysqldb
* mysql-server

## Database setup

The database is used to store climate data, and for the application
to look up the climate data and display it to the user.

Run the scripts in the `sql/` folder as the `climate_map` user.
Make sure you change the password of the `climate_map` user.

```
mysql -u root
\. sql/create-db.sql

mysql -u climate_map
\. sql/create-tables.sql
\. sql/insert-meta-data.sql
SET PASSWORD FOR climate_map = PASSWORD('a_mKWpF60'); -- Change this!
```

You then need to import climate datasets into this database.

## Nginx setup

Use the following nginx config to serve the climate map.

```
server {
    listen              80;
    server_name         climatemap;
    root                /path/to/climate-map/public;
    index               index.html;

    location /api {
        rewrite             ^/api/(.*)      /$1 break;
        proxy_set_header    X-Forwarded-For $remote_addr;
        proxy_set_header    Host $http_host;
        proxy_pass          "http://127.0.0.1:5000";
    }
}
```

## Running the API web server

Run this in bash:

```
FLASK_APP=src/climatapi.py flask run
```

# Important notes

* Coordinates in Postgis and geoJSON are `[longitude, latitude]`, but coordinates
in the datasets and the transformation code are `[latitude, longitude]`. Make sure
you know which is which in every case.

* OpenStreetMap's coordinates go from latitude 85.051129 to -85.051129, so any images
should map to those bounds, or they may not align with the OSM tiles. See
[Web Mercator projection](https://en.wikipedia.org/wiki/Web_Mercator_projection#Formulas).

# Data source(s)

* [ESRL : PSD : All Gridded Datasets](https://www.esrl.noaa.gov/psd/data/gridded/)

# Data transformation

You can transform the data from the NOAA or WorldClim (assuming permission allows) using
`transform-dataset.py`.
This data transformation script is used to process the netCDF4 files into
various formats (including inserting into the database) so that the web application can
read the climate data from the server.

The script takes input file and output file as arguments. The script will detect
the desired format based on the output file extension.

University of Delaware gridded temperature and precipitation data can be used
for this purpose, but other datasets may be used as well if they are in
netCDF4 format and are grouped by month.

Also WorldClim geotiff data that is 2-dimensional and already aggregated by month can also
be used.

CMIP6 and TerraClimate data are also supported.

## Transforming to database

Use these commands to load the climate data to the database.
```
bin/transform-dataset.py tmean_5m_bil/ localhost:climate_map:climate_map tavg 1960 1990 1 worldclim
bin/transform-dataset.py tmean_5m_bil/ localhost:climate_map:climate_map tavg 1960 1990 2 worldclim
...
bin/transform-dataset.py tmean_5m_bil/ localhost:climate_map:climate_map tavg 1960 1990 12 worldclim

bin/transform-dataset.py tmin_5m_bil/ localhost:climate_map:climate_map tmin 1960 1990 1 worldclim
...

bin/transform-dataset.py tmax_5m_bil/ localhost:climate_map:climate_map tmax 1960 1990 1 worldclim
...

bin/transform-dataset.py precip_5m_bil/ localhost:climate_map:climate_map precip 1960 1990 1 worldclim
...
```

The 2nd argument is the connection string and is of the form `<host>:<db>:<user>`.
You could put the password in `.pgpass` or specify it as `<host>:<db>:<user>:<password>`.

The last argument is the data source and is required to identify the data source of all
values. For example, we can provide both NOAA data and WorldClim data! But we'll need
to specify which data are of which data source.

To do load data for all months, you can run the transform-all-months script:

```
bin/transform-all-months.sh TerraClimate19812010_tmin.nc tmin 1891 2010 TerraClimate
bin/transform-all-months.sh TerraClimate19812010_tmax.nc tmax 1891 2010 TerraClimate
bin/transform-all-months.sh TerraClimate19812010_ppt.nc ppt 1891 2010 TerraClimate
```

Or:
```
bin/transform-all-months.sh tmean_5m_bil/ tavg 1960 1990 worldclim
bin/transform-all-months.sh prec_5m_bil/ precip 1960 1990 worldclim
...
```

## Transforming to PNG tiles

To improve efficiency, tiles can be generated that divide the map so that Leaflet
does not have to load the entire contour map. We use the same map tiling system
that OSM uses as Leaflet has built-in support for it. These are stored in a folder
structure similar to the above, and can be created by transform script by
specifying that the output folder ends with `/tiles/{full_variable_name}`:

```
bin/transform-dataset.py tmean_5m_bil/ public/data/worldclim/1960-1990/tiles/temperature-avg-01 tavg 1960 1990 0 worldclim
bin/transform-dataset.py tmean_5m_bil/ public/data/worldclim/1960-1990/tiles/temperature-avg-01 tavg 1960 1990 1 worldclim
...

bin/transform-dataset.py precip_5m_bil/ public/data/worldclim/1960-1990/tiles/precipitation-01 precip 1960 1990 1 worldclim
...
```

Month `0` is all-months so you can have a map that shows annual average temperature
or precipitation.

You can also specify minimum and maximum temperature datasets if you do not have
average temperature in a dataset (useful for saving space as these files
can be quite large):

```
bin/transform-dataset.py TerraClimate19812010_tmin.nc TerraClimate19812010_tmax.nc public/data/TerraClimate/1981-2010/tiles/temperature-avg-01 tavg 1981 2010 1 TerraClimate

bin/transform-dataset.py TerraClimate19812010_ppt.nc public/data/TerraClimate/1981-2010/tiles/precipitation-01 ppt 1981 2010 1 TerraClimate
```

To do this for all months, you can run the all-months script:

```
bin/transform-all-months-tiles.sh tmean_5m_bil/ tavg 1960 1990 worldclim
bin/transform-all-months-tiles.sh prec_5m_bil/ precip 1960 1990 worldclim
...
```

Or:

```
bin/transform-all-months-tiles.sh TerraClimate19812010_tmin.nc TerraClimate19812010_tmax.nc tavg 1981 2010 TerraClimate
bin/transform-all-months-tiles.sh TerraClimate19812010_ppt.nc ppt 1981 2010 TerraClimate
```

# Tiling scheme

## OSM tiling

Given the lack of documentation surrounding the OSM tiling system, here
is how the map tiles correspond to the division of the world map.
If it's there, sorry, but I looked and looked.

For each zoom level, the map is divided by 2 lengthwise and 2 widthwise.
It starts at one tile for the entire world at zoom level 0, consisting
of 256x256 pixels. Then at zoom level 1 there are 2x2 tiles, also being
256x256 pixels each.

For each increase in zoom level, the number of tiles widthwise and lengthwise
doubles.

To request a given tile for a part of the map, a request that ends with
`/{z}/{x}/{y}.jpeg` must be made, where `{z}` is the zoom level, and x and y are
the tile indexes starting at `0`. For zoom level `z`, the maximum tile index
for the zoom level is `2^z - 1`. For example, to request the one tile at zoom level
0, make a request to `/0/0/0.jpeg`. For zoom level 4, you can request tile
`/4/15/15.jpeg` but x and y cannot be greater than that.
