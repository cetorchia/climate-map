# Climate map

Copyright (c) 2020 Carlos Emilio Torchia

# System requirements

The following system specifications are recommended.

* RAM: At least 2 GB of RAM, preferably at least 4 GB
* CPU: At least 2 GHz and 2 cores or more
* Disk space: depending on how many different models you allow the user to select
you may need 40 GB of disk space.

# Installation

To install the climate map, first use npm to build the javascript.

```
npm run build-dev       # Development environment (your local machine)
npm run build           # Production environment (your web host)
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

Specify the database connection details in the `config/config.yaml`
file. See `config/config.yaml.example`.

You then need to import climate datasets into this database.

## Nginx setup

Use the following nginx config to serve the climate map.

```
proxy_cache_path /tmp/api_cache levels=1:2 keys_zone=api_cache:60m max_size=1g 
                 inactive=60m use_temp_path=off;

server {
    listen              80;
    server_name         climatemap;
    root                /path/to/climate-map/public;
    index               index.html;

    location /api {
        rewrite             ^/api/(.*)      /$1 break;
        proxy_set_header    X-Forwarded-For $remote_addr;
        proxy_set_header    Host $http_host;
        proxy_cache         api_cache;
        proxy_cache_valid   200 60m;
        proxy_pass          "http://127.0.0.1:5000";
    }

    # Credit to https://serverfault.com/a/571403
    # Credit to https://serverfault.com/a/319657
    location ~ ^/.+\.(?:ico|css|js|gif|jpe?g|png)$ {
        expires 7d;
        add_header Pragma "public";
        add_header Cache-Control "public";
        access_log /dev/null;
        error_log /dev/null;
    }

    location /location {
        rewrite ^/location/([^/]+)$ /index.html?location=$1 last;
        rewrite ^/location/ /index.html last;
    }

    location /index.html {
        if ($arg_location) {
            set $title "Climate of $arg_location";
        }
        if ($arg_location = "") {
            set $title "Climate Map";
        }
        sub_filter "<title>Climate Map</title>" "<title>$title</title>";
        sub_filter "<meta name=\"description\" content=\"Climate map showing past and future temperature and precipitation\">" "<meta name=\"description\" content=\"$title\">";
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

## Transforming datasets into the database

Use this command to load the climate data to the database as in the following
example.

```
bin/transform-dataset.py TerraClimate19812010_tavg.nc tavg 1981 2010 TerraClimate
bin/transform-dataset.py TerraClimate19812010_tmin.nc tmin 1981 2010 TerraClimate
bin/transform-dataset.py TerraClimate19812010_ppt.nc precip 1981 2010 TerraClimate

bin/transform-dataset.py tas_day_CanESM5_historical_r1i1p1f1_gn_18500101-20141231.nc tas 2015 2045 CanESM5.historical
bin/transform-dataset.py tasmin_day_CanESM5_historical_r1i1p1f1_gn_18500101-20141231.nc tasmin 2015 2045 CanESM5.historical
bin/transform-dataset.py pr_day_CanESM5_historical_r1i1p1f1_gn_18500101-20141231.nc pr 2015 2045 CanESM5.historical

bin/transform-dataset.py tas_day_CanESM5_ssp245_r1i1p1f1_gn_20150101-21001231.nc tas 2015 2045 CanESM5.ssp245
bin/transform-dataset.py tasmin_day_CanESM5_ssp245_r1i1p1f1_gn_20150101-21001231.nc tasmin 2015 2045 CanESM5.ssp245
bin/transform-dataset.py pr_day_CanESM5_ssp245_r1i1p1f1_gn_20150101-21001231.nc pr 2015 2045 CanESM5.ssp245
```

Note that maximum temperature datasets do not need to be loaded as it can be
calculated using average and minimum temperature.

## Calibrating projection datasets against historical data

After loading projections for the future, you can calibrate this data so that
the user is comparing "apples to apples". This means adding the projected changes
to the baseline historical data (e.g. TerraClimate, WorldClim) in order to derive
a high-resolution projection dataset. This allows the user to visualize the changes
much more effectively, but involves deviating from what the model actually says.

When you run the calibration script, you need to specify both the baseline historical
dataset as well as the historical model output in order for the script to know
the projected differences and add those to the baseline data.

```
bin/calibrate-dataset.py TerraClimate CanESM5.historical CanESM5.ssp245 tavg 1981-2010 2015-2045
bin/calibrate-dataset.py TerraClimate CanESM5.historical CanESM5.ssp245 tmin 1981-2010 2015-2045
bin/calibrate-dataset.py TerraClimate CanESM5.historical CanESM5.ssp245 precip 1981-2010 2015-2045
```

This will generate a new dataset with the same data source name with a "calibrated"
flag. This flag distinguishes that dataset so it can be identified separately in
the application.

## Generating PNG tiles

To improve efficiency, tiles are generated that divide the map so that Leaflet
does not have to load the entire contour map. We use the same map tiling system
that OSM uses as Leaflet has built-in support for it. These are stored in a folder
structure that allows lookup by zoom level, and X and Y tile positions.

Once you have loaded a dataset into the database, you can generate tiles for it
using the script used in the following example.

```
bin/tiles-from-dataset.py TerraClimate tavg 2015 2045 0
bin/tiles-from-dataset.py TerraClimate precip 2015 2045 0

bin/tiles-from-dataset.py MRI-ESM2-0.ssp245 tavg 2015 2045 1
bin/tiles-from-dataset.py MRI-ESM2-0.ssp245 precip 2015 2045 1
```

You have to specify whether the script is calibrated using the last parameter.

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
