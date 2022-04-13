# Climate map

Copyright (c) 2020 Carlos Emilio Torchia

# About

Climate Map is a web application showing the user a map with colours representing
temperature, precipitation, and other climate normals. The user can also click
on the map and see climate normals for a specified location. This repo contains
both an Python API, JavaScript UI, and Python scripts to load climate datasets
into the database.

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

Please don't worry; this is actually really easy. Just look at one step at a time.

Install the following Ubuntu packages, or equivalent:

API and web server:
* npm
* python3
* python3-numpy
* python3-opencv
* python3-flask
* python3-mysqldb
* mysql-server
* nginx
* uwsgi
* uwsgi-plugin-python3

Climate data transformation and tile generation:
* python3-netcdf4
* python3-gdal
* python3-cdo
* python3-matplotlib

See the other `README-*.md` files for other packages that may or may not be
necessary, e.g. for system administration and base map tile generation.

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
(The actual climate is stored as numpy memory maps, but meta data
about the datasets are stored in MySQL.)

Run the scripts in the `sql/` folder as the `climate_map` user.
Make sure you change the password of the `climate_map` user.

```
mysql -u root
\. sql/create-db.sql

mysql -u climate_map
\. sql/create-tables.sql
\. sql/insert-meta-data.sql
SET PASSWORD FOR climate_map = PASSWORD('a_mKWpF60'); -- MySQL 5.7.5 or earlier
ALTER USER 'climate_map' IDENTIFIED BY 'a_mKWpF60'; -- Change this! 5.7.6 or later
```

Specify the database connection details in the `config/config.yaml`
file. See `config/config.yaml.example`.

You should also specify database connection details in your `.my.cnf`
in order to be able to use the `mysql` command-line client to access
the database. Paste the following in `~/.my.cnf`:

```
[client]
user = climate_map
password = <password>
```

You then need to import climate datasets into this database. See the
[Data transformation](#data-transformation) section.

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
        rewrite ^/location/ /index.html last;
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
traffic headed to `/api/*` to the server running on port 5000.

Create `/etc/uwsgi/apps-available/climatapi.ini` to have:

```
[uwsgi]
plugin = python3
chdir = /path/to/climate-map
pythonpath = /path/to/climate-map/src
wsgi-file = src/climatapi.py
callable = app
http-socket = :5000         # Replace with http = 127.0.0.1:5000 for Ubuntu 18.04
processes = 3
```

The tile API server (`/tiles/*`) runs on port 5001.
Create `/etc/uwsgi/apps-available/tile-api.ini` to have:

```
[uwsgi]
plugin = python3
chdir = /path/to/climate-map
pythonpath = /path/to/climate-map/src
wsgi-file = src/tile-api.py
callable = app
http-socket = :5001         # Replace with http = 127.0.0.1:5001 for Ubuntu 18.04
processes = 3
disable-logging = True
```

Then run:

```
sudo ln -s /etc/uwsgi/apps-available/climatapi.ini /etc/uwsgi/apps-enabled/
sudo ln -s /etc/uwsgi/apps-available/tile-api.ini /etc/uwsgi/apps-enabled/
sudo service uwsgi restart
```

# Data transformation

You can transform the data from the NOAA, WorldClim, and other datasets
(assuming permission allows) using the scripts described below.

These data transformation scripts are used to process the netCDF4 files into
numpy arrays grouped by month as well as coloured climate tiles so that the
web application can read these climate data from the server and display them
to the user.

Input datasets must be gridded datasets indexed by time, latitude, and longitude.
They can be grouped by month or day, and they can be multi-year or aggregated.

CMIP6 and TerraClimate data are supported and used by default in the main
update script.

## Finding datasets

You can find gridded climate datasets in a variety of places, depending on whether you're
looking for historical observations or model projections.

TerraClimate, WorldClim, and NOAA provide historical datasets.

* NOAA: https://psl.noaa.gov/data/gridded/
* WorldClim: https://worldclim.org/
* TerraClimate: http://www.climatologylab.org/terraclimate.html

CMIP6 provides model projections:

* https://esgf-node.llnl.gov/search/cmip6/

## Configuring the update script

The update script uses `config/config-update.yaml` to tell it what to download
and transform. Some measurements like potential evapotranspiration are not
available for all models. This config file will tell which datasets to retrieve
and which measurements for each model to load, among other information.

The information in this config file should be straightforward to understand without explanation.

For example, the following snippet would tell the update script to load
experiments `ssp126` and `1pctCO2` for `CanESM5`. And the measurements to
be loaded are average temperature, minimum temperature, and precipitation.
And the date ranges to be loaded are 2021-2050 and 2061 to 2090.

```
models:
  CanESM5:
    experiments:
      - ssp126
      - 1pctCO2
    measurements:
      - tavg
      - tmin
      - precip
    date_ranges:
      - '2021-2050'
      - '2061-2090'
```

With this configuration, the update script would download the specified model
output from one of the CMIP6 data nodes automatically (using `get-dataset.py`).

The config file also tells what URL to download historical data. Since this
may be outdated, you may have to update this.

## Update script

The update script has several commands for loading datasets preloaded.
You can run it as follows:

```
bin/update.sh
```

Open and look at `update.sh` to see which datasets come by default.

To update individual datasets, you can run similar to the following with
any specified model and measurement:

```
bin/update-dataset.sh TerraClimate tavg
bin/update-dataset.sh TerraClimate tmin
bin/update-dataset.sh TerraClimate precip
bin/update-dataset.sh TerraClimate potet

bin/update-dataset.sh CanESM5 tavg
bin/update-dataset.sh CanESM5 tmin
bin/update-dataset.sh CanESM5 precip
bin/update-dataset.sh CanESM5 potet

...
```

This will take care of downloading, transforming, and loading the specified
datasets.

The commands below are run by the above commands, but you may need to run
them individually sometimes. And you'll have to modify them if they cannot
understand a new dataset you are trying to load. Inevitably you'll have
to modify the code if you want to add new variables such as runoff or
soil moisture.

## Getting datasets from the internet

The following script can be used to download TerraClimate and CMIP6.

```
bin/get-dataset.py TerraClimate tmin
bin/get-dataset.py TerraClimate tmax
bin/get-dataset.py TerraClimate ppt
bin/get-dataset.py TerraClimate elevation

bin/get-dataset.py CNRM-CM6-1 tasmin
bin/get-dataset.py CNRM-CM6-1 tas
bin/get-dataset.py CNRM-CM6-1 pr
```

**N.B.**: that you have to specify the variable name specified on the remote server,
not the measurement code in the measurements table in the MySQL database.
For example, TerraClimate calls precipitation "ppt", whereas Climate Map
calls it "precip". In most of these commands you must provide the Climate Map
measurement, but for `get-dataset.py` you must provide the remote variable name.

## Transforming datasets into the database

Use the transform script to load the climate data to the database.
The script takes input file, measurement, date range, and data source as arguments.
It will detect the desired format based on the output file extension.
These can be netCDF4, GeoTIFF, or anything `gdal` can handle. Units can be
in Kelvin, Celsius, mm, or kg/m^2/s (or "kg m-2 s-1", which is the same as mm/s).

```
bin/transform-dataset.py TerraClimate19812010_tmin.nc TerraClimate19812010_tmax.nc tavg 1981 2010 TerraClimate
bin/transform-dataset.py TerraClimate19812010_tmin.nc tmin 1981 2010 TerraClimate
bin/transform-dataset.py TerraClimate19812010_ppt.nc precip 1981 2010 TerraClimate

bin/transform-dataset.py tas_day_CanESM5_historical_r1i1p1f1_gn_18500101-20141231.nc tas 2015 2045 CanESM5.historical
bin/transform-dataset.py tasmin_day_CanESM5_historical_r1i1p1f1_gn_18500101-20141231.nc tasmin 2015 2045 CanESM5.historical
bin/transform-dataset.py pr_day_CanESM5_historical_r1i1p1f1_gn_18500101-20141231.nc pr 2015 2045 CanESM5.historical

bin/transform-dataset.py tas_day_CanESM5_ssp245_r1i1p1f1_gn_20150101-21001231.nc tas 2015 2045 CanESM5.ssp245
bin/transform-dataset.py tasmin_day_CanESM5_ssp245_r1i1p1f1_gn_20150101-21001231.nc tasmin 2015 2045 CanESM5.ssp245
bin/transform-dataset.py pr_day_CanESM5_ssp245_r1i1p1f1_gn_20150101-21001231.nc pr 2015 2045 CanESM5.ssp245
```

You can pass multiple files to the script, and it will calculate the average of
all of them. This is useful if you only have maximum and minimum datasets but
not average.
```
bin/transform-dataset.py TerraClimate19812010_tmin.nc TerraClimate19812010_tmax.nc tavg 1981 2010 TerraClimate
```

Note that maximum temperature datasets do not need to be loaded as it can be
calculated using average and minimum temperature. However you must have average
temperature datasets in order to draw the coloured climate tiles.

If you have two separate files for the same measurement but for different
time ranges, and you want to average them, then you have to use `cdo` to
combine them first.

```
cdo -selall file1.nc file2.nc file.nc
```

This is done automatically by `get-dataset.py` when you retrieve a dataset
that is split up over different time ranges.

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
#bin/calibrate-dataset.py TerraClimate CanESM5.historical CanESM5.ssp245 tmax 1981-2010 2015-2045
bin/calibrate-dataset.py TerraClimate CanESM5.historical CanESM5.ssp245 precip 1981-2010 2015-2045

bin/calibrate-dataset.py TerraClimate CanESM5.historical CanESM5.ssp245 tavg 1981-2010 2045-2075
bin/calibrate-dataset.py TerraClimate CanESM5.historical CanESM5.ssp245 tmin 1981-2010 2045-2075
#bin/calibrate-dataset.py TerraClimate CanESM5.historical CanESM5.ssp245 tmax 1981-2010 2045-2075
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

The following command is a shortcut to generate tiles for the model for all
scenarios, and date ranges. (It automatically uses the calibrated dataset.)

```
bin/generate-tiles.sh MRI-ESM2-0 tavg
bin/generate-tiles.sh MRI-ESM2-0 tmin
bin/generate-tiles.sh MRI-ESM2-0 precip
```

## Loading elevation data

For loading elevation data from a netCDF4 dataset, you can use the following command

```
bin/load-nontemporal-data.py terraclim_dem.nc elevation TerraClimate
```

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
bin/deploy.sh myclimatemap.org --code
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

You can also deploy other things, see the usage for full details.

```
bin/deploy.sh myclimatemap.org --geonames
bin/deploy.sh myclimatemap.org --map-tiles
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

You also need to specify the connection details for the `mysql` command-line
client on the server, because the `deploy.sh` script uses it. Paste the following
into `~/.my.cnf` on the web server in the `climatemap` user's home directory:

```
[client]
user = climate_map
password = <password>
```

## Nginx

Set up nginx as described above.

## uWSGI

Set up uWSGI as described above.
Whenever the API code changes you have to restart uWSGI.

# Important notes

* Coordinates in Postgis and geoJSON are `[longitude, latitude]`, but coordinates
in the datasets and the transformation code are `[latitude, longitude]`. Make sure
you know which is which in every case.

* OpenStreetMap's coordinates go from latitude 85.051129 to -85.051129, so any images
must map to those bounds, or they may not align with the OSM tiles. See
[Web Mercator projection](https://en.wikipedia.org/wiki/Web_Mercator_projection#Formulas).

* NetCDF4 climate model outputs often use a 360 day calendar to make it "easier" to
generate monthly climate normals. This apparently will not make grouping by month
inaccurate. The transform code now supports the 360 day calendar using the `netcdftime`
module.
See my question here for more details:
[Create a netcdf time Dimension using a 360 day calendar](https://gist.github.com/paultgriffiths/266ffe20a2d0d3ac8985#gistcomment-3290314)

* CMIP6 datasets often have multiple variants for each model. Usually they
start with the one called "r1i1p1f1", but sometimes this one does not exist.
The `config/config-update.yaml` file specifies which variants the `get-dataset.py`
script tries to fetch. If none of them exist for the desired model, you will
need to add a variant label that does exist to the `variant` field in the config.

* To add a new type of measurement, such as soil moisture, add a record to the
`measurements` table. Ideally, add the record to `sql/insert-meta-data.sql` to
keep track of it. You will also have to modify the code in several places.
TODO: Document where the code would need to be modified.

* When updating any JavaScript or CSS code, after running `npm run build`, it is
recommended that you update the hash of `climate-map.bundle.js` in `public/index.html`
before deploying the code to the production site.
The hash can be found in the output of `npm run build` beside `climate-map.js`.

```
<script type="text/javascript" src="/climate-map.bundle.js?hash=58fce162760b3b36b1b5"></script>
```

Doing this will force the update of all javascript and CSS code by the user's browser cache.
If not, they have to press Ctrl+Shift+R to force a refresh. Another option is to put your
release version as a query parameter instead of the hash.

* If you update any API code (including the tile API) you have to run `service uwsgi restart`.
