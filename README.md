# Climate map

Copyright (c) 2020 Carlos Emilio Torchia

# System requirements

The following system specifications are recommended.

* RAM: At least 2 GB of RAM, preferably at least 4 GB
* CPU: At least 2 GHz and 2 cores or more
* Disk space: Depending on how many different climate models you provide the user,
you may need 40 GB of disk space, or more, or less. Check the disk usage of the data/
folder and the public/ folder after the transformations below have been completed.
* OS: Ubuntu 18.04

# Server setup

See [README-server.md](README-server.md)

# Installation

Install the following Ubuntu packages, or equivalent:

* npm
* python3
* python3-numpy
* python3-netcdf4
* python3-gdal
* python3-matplotlib
* python3-opencv
* python3-flask
* python3-mysqldb
* mysql-server
* nginx
* uwsgi
* uwsgi-plugin-python3

## JavaScript setup

Use npm to build the javascript.

```
npm install
npm run build-dev       # Development environment (your local machine)
npm run build           # Production environment (your web host)
```

Configure the javascript in `config/config.json`.
See `config/config.json.example`.

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
proxy_cache_path /tmp/tile_cache levels=1:2 keys_zone=tile_cache:60m max_size=10g 
                 inactive=30d use_temp_path=off;

proxy_cache_path /tmp/api_cache levels=1:2 keys_zone=api_cache:60m max_size=1g 
                 inactive=60m use_temp_path=off;

server {
    listen 80;
    listen [::]:80 default_server;
    server_name myclimatemap.org;
    return 301 https://$host$request_uri;
}

server {
    listen              443 ssl;
    server_name         myclimatemap.org;
    keepalive_timeout   70;

    ssl_session_cache   shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_certificate     /etc/ssl/climatemap/cert.pem;
    ssl_certificate_key /etc/ssl/climatemap/key.pem;
    ssl_protocols       TLSv1 TLSv1.1 TLSv1.2;
    ssl_ciphers         HIGH:!aNULL:!MD5;

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

    location ~ ^/tiles/ {
        rewrite             ^/tiles/(.*)    /$1 break;
        proxy_set_header    X-Forwarded-For $remote_addr;
        proxy_set_header    Host $http_host;
        proxy_cache         tile_cache;
        proxy_cache_valid   200 30d;
        proxy_pass          "http://127.0.0.1:5001";
        access_log          /dev/null;
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
```

If you do not have a SSL certificate, you can generate a self-signed key.
Otherwise use the certificate provided by your CA.

```
sudo openssl req -x509 -newkey rsa:4096 -keyout /etc/ssl/climatemap/key.pem -out /etc/ssl/climatemap/cert.pem -nodes
```

Then run:

```
sudo ln -s /etc/nginx/sites-available/climate-map.conf /etc/nginx/sites-enabled/
sudo service nginx restart
```

## uWSGI

uWSGI is used to run the API server. The main nginx server passes
traffic headed to `/api/` to the server running on port 5000.
Create `/etc/uwsgi/apps-available/climatapi.ini` to have:

```
[uwsgi]
plugin = python3
chdir = /path/to/climate-map
pythonpath = /path/to/climate-map/src
wsgi-file = src/climatapi.py
callable = app
http = 127.0.0.1:5000
processes = 3
```

Also create `/etc/uwsgi/apps-available/tile-api.ini` to have:

```
[uwsgi]
plugin = python3
chdir = /path/to/climate-map
pythonpath = /path/to/climate-map/src
wsgi-file = src/tile-api.py
callable = app
http = 127.0.0.1:5001
processes = 3
```

Then run:

```
sudo ln -s /etc/uwsgi/apps-available/climatapi.ini /etc/uwsgi/apps-enabled/
sudo ln -s /etc/uwsgi/apps-available/tile-api.ini /etc/uwsgi/apps-enabled/
sudo service uwsgi restart
```

# Important notes

* Coordinates in Postgis and geoJSON are `[longitude, latitude]`, but coordinates
in the datasets and the transformation code are `[latitude, longitude]`. Make sure
you know which is which in every case.

* OpenStreetMap's coordinates go from latitude 85.051129 to -85.051129, so any images
should map to those bounds, or they may not align with the OSM tiles. See
[Web Mercator projection](https://en.wikipedia.org/wiki/Web_Mercator_projection#Formulas).

* When updating the code in `climate-map.js`, after running `npm run build`, it is
recommended that you update the hash of `climate-map.bundle.js` in `public/index.html`.
This will force the update of that file by the user's browser cache. If not, they
have to press Ctrl+Shift+R to force a refresh. Another option is to put your release
version.

```
<script type="text/javascript" src="/climate-map.bundle.js?hash=58fce162760b3b36b1b5"></script>
```

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
bin/calibrate-dataset.py TerraClimate CanESM5.historical CanESM5.ssp245 tmax 1981-2010 2015-2045
bin/calibrate-dataset.py TerraClimate CanESM5.historical CanESM5.ssp245 precip 1981-2010 2015-2045

bin/calibrate-dataset.py TerraClimate CanESM5.historical CanESM5.ssp245 tavg 1981-2010 2045-2075
bin/calibrate-dataset.py TerraClimate CanESM5.historical CanESM5.ssp245 tmin 1981-2010 2045-2075
bin/calibrate-dataset.py TerraClimate CanESM5.historical CanESM5.ssp245 tmax 1981-2010 2045-2075
bin/calibrate-dataset.py TerraClimate CanESM5.historical CanESM5.ssp245 precip 1981-2010 2045-2075
```

This will generate a new dataset with the same data source name with a "calibrated"
flag. This flag distinguishes that dataset in order to generate tiles for the
calibrated dataset and not the uncalibrated one.

## Generating PNG tiles

To improve efficiency, tiles are generated that divide the map so that Leaflet
does not have to load the entire contour map. We use the same map tiling system
that OSM uses as Leaflet has built-in support for it. These are stored in a folder
structure that allows lookup by zoom level, and X and Y tile positions.

Once you have loaded a dataset into the database, you can generate tiles for it
using the script used in the following example.

```
bin/tiles-from-dataset.py TerraClimate tavg 1981 2010
bin/tiles-from-dataset.py TerraClimate precip 1981 2010

bin/tiles-from-dataset.py --calibrated MRI-ESM2-0.ssp245 tavg 2015 2045
bin/tiles-from-dataset.py --calibrated MRI-ESM2-0.ssp245 precip 2015 2045
```

You have to specify the `--calibrated` option if the dataset is calibrated,
in order to generate tiles for the calibrated dataset instead of the uncalibrated
dataset.

# Tiling scheme

## OSM tiling

Here is how the map tiles correspond to the division of the world map.
This is also documented at
[Zoom levels - OpenStreetMap Wiki](https://wiki.openstreetmap.org/wiki/Zoom_levels).

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

# Server Deployment

The deploy script is used to send files to the server. SSH is used.

```
bin/deploy.sh myclimatemap.org
bin/deploy.sh myclimatemap.org --tiles
bin/deploy.sh myclimatemap.org --data
```

To configure the climate map, you must update the config file on the server.

```
ssh myclimatemap.org
cd climate-map
vim config/config.yaml
cp config/config.json.example config/config.json
```

Next, build the javascript.

```
bin/deploy.sh myclimatemap.org --build
```

## Database setup

To copy your local database to the server (assuming all transformations were
done locally and not on the server), you can run the following.

```
localhost$ mysqldump climate_map > climate_map.sql
localhost$ scp climate_map.sql myclimatemap.org:climate-map/
localhost$ ssh myclimatemap.org
myclimatemap.org$ cd climate-map
myclimatemap.org$ mysql -u root
mysql> \. sql/create-db.sql
mysql> SET PASSWORD FOR climate_map = PASSWORD('a_mKWpF60'); -- Change this!
myclimatemap.org$ mysql -u climate_map
mysql> \. climate_map.sql
```

Again, make sure to **change the password** of the climate_map user for security!

## Nginx

Set up nginx as described above.

## uWSGI

Set up uWSGI as described above.
Whenever the API code changes you have to restart uWSGI.
