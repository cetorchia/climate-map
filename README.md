# Installation

Use npm to build the javascript output.

```
npm run build
```

Install the following Ubuntu packages, or equivalent:

* python3-numpy
* python3-netcdf4
* python3-gdal
* python3-png
* python3-matplotlib
* python3-opencv
* python3-flask
* python3-psycopg2
* postgresql-10
* postgresql-10-postgis-2.4

## Database set up

The database is used to store climate data, and for the application
to look up the climate data and display it to the user.

Run the scripts in the `sql/` folder as the `postgres` user.
Make sure you change the password of the `climate_map` user.

```
sudo -u postgres psql
\i sql/create-db.sql
\i sql/create-tables.sql
\i sql/insert-meta-data.sql
ALTER USER climate_map WITH PASSWORD 'a_mKWpF60)'; -- Change this!
```

You may need to change the `pg_hba.conf` file to allow the climate map user to
connect with an md5-hashed password (i.e. not using peer authentication).

```
local   all             all                                     md5
```

# Important notes

* Coordinates in OSM and geoJSON are `[longitude, latitude]`, but coordinates
in the datasets and the transformation code are `[latitude, longitude]`. Make sure
which is which in every case.

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

## Transforming to PNG files

These files are used to overlay a PNG representation of the climate data
on the map. This can allow the browser to render colours for different temperatures
or precipitation much quicker than plotting polygons for data it would have to load.

```
# Generate temperature datasets
bin/transform-dataset.py air.mon.mean.v501.nc public/data/1980-2010/temperature-avg.png air 1980 2010
bin/transform-dataset.py air.mon.mean.v501.nc public/data/1980-2010/temperature-avg-01.png air 1980 2010 1
bin/transform-dataset.py air.mon.mean.v501.nc public/data/1980-2010/temperature-avg-02.png air 1980 2010 1
...
bin/transform-dataset.py air.mon.mean.v501.nc public/data/1980-2010/temperature-avg-12.png air 1980 2010 12

# Generate precipitation datasets
bin/transform-dataset.py precip.mon.total.v501.nc public/data/1980-2010/precipitation.png precip 1980 2010
bin/transform-dataset.py precip.mon.total.v501.nc public/data/1980-2010/precipitation-01.png precip 1980 2010 1
bin/transform-dataset.py precip.mon.total.v501.nc public/data/1980-2010/precipitation-02.png precip 1980 2010 2
...
bin/transform-dataset.py precip.mon.total.v501.nc public/data/1980-2010/precipitation-12.png precip 1980 2010 12
```

The following script does each month in one command for convenience.

```
bin/transform-all-months-png.sh air.mon.mean.v501.nc air 1970 2000
bin/transform-all-months-png.sh air.mon.mean.v501.nc air 1980 2010
bin/transform-all-months-png.sh precip.mon.mean.v501.nc precip 1970 2000
bin/transform-all-months-png.sh precip.mon.mean.v501.nc precip 1980 2010
...
```

## WorldClim transformations

**N.B.**: For WorldClim data, pass the entire folder as the first argument, but use
"tavg" as the variable name instead of "air". This applies to the other usages below.
The "precip" variable name for precipitation must still be used with WorldClim.

```
bin/transform-all-months-png.sh wc2.0_5m_tavg tavg 1970 2000
bin/transform-all-months.sh wc2.0_5m_tavg tavg 1970 2000

bin/transform-all-months-png.sh wc2.0_5m_prec precip 1970 2000
bin/transform-all-months.sh wc2.0_5m_prec precip 1970 2000
```

## Transforming to indexed JSON files

These files contain data for individual coordinates. They are stored in folders
by their coordinates making looking up data for a single pair of coordinates
simple and efficient. For example, the file path for the JSON file
containing data for `[-13.75, -172.25]` during 1970-2000
would be `public/data/1970-2000/coords/-20/-180/-13.75_-172.25.json`.
Future plan is to use a database server.

```
# Generate temperature datasets
bin/transform-dataset.py air.mon.mean.v501.nc public/data/1980-2010/ air 1980 2010
bin/transform-dataset.py air.mon.mean.v501.nc public/data/1980-2010/ air 1980 2010 1
bin/transform-dataset.py air.mon.mean.v501.nc public/data/1980-2010/ air 1980 2010 2
...
bin/transform-dataset.py air.mon.mean.v501.nc public/data/1980-2010/ air 1980 2010 12

# Generate precipitation datasets
bin/transform-dataset.py precip.mon.total.v501.nc public/data/1980-2010/ precip 1980 2010
bin/transform-dataset.py precip.mon.total.v501.nc public/data/1980-2010/ precip 1980 2010 1
bin/transform-dataset.py precip.mon.total.v501.nc public/data/1980-2010/ precip 1980 2010 2
...
bin/transform-dataset.py precip.mon.total.v501.nc public/data/1980-2010/ precip 1980 2010 12
```

The following script does each month in one command for convenience.

```
bin/transform-all-months.sh air.mon.mean.v501.nc air 1970 2000
bin/transform-all-months.sh air.mon.mean.v501.nc air 1980 2010
bin/transform-all-months.sh precip.mon.mean.v501.nc precip 1970 2000
bin/transform-all-months.sh precip.mon.mean.v501.nc precip 1980 2010
...
```

## Transforming to bulk JSON files

These files individually contain data for all coordinates, and as such the files
can be very large and inefficient for the web application to load.

```
# Generate temperature datasets
bin/transform-dataset.py air.mon.mean.v501.nc public/data/1980-2010/temperature-avg.json air 1980 2010
bin/transform-dataset.py air.mon.mean.v501.nc public/data/1980-2010/temperature-avg-01.json air 1980 2010 1
bin/transform-dataset.py air.mon.mean.v501.nc public/data/1980-2010/temperature-avg-02.json air 1980 2010 2
...

# Generate precipitation datasets
bin/transform-dataset.py precip.mon.total.v501.nc public/data/1980-2010/precipitation.json precip 1980 2010
bin/transform-dataset.py precip.mon.total.v501.nc public/data/1980-2010/precipitation-01.json precip 1980 2010 1
bin/transform-dataset.py precip.mon.total.v501.nc public/data/1980-2010/precipitation-02.json precip 1980 2010 2
...
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

To request a given tile for a part of the map, a request the ends with
`/{z}/{x}/{y}.png` must be made, where `{z}` is the zoom level, and x and y are
the tile indexes starting at `0`. For zoom level `z`, the maximum tile index
for the zoom level is `2^z - 1`. For example, to request the one tile at zoom level
0, make a request to `/0/0/0.png`. For zoom level 4, you can request tile
`/4/15/15.png` but x and y cannot be greater than that.

## Map tiling

To improve efficiency, tiles can be generated that divide the map so that Leaflet
does not have to load the entire contour map. We use the same map tiling system
that OSM uses as Leaflet has built-in support for it. These are stored in a folder
structure similar to the above, and can be created by transform script by
specifying that the output folder ends with `/tiles/{full_variable_name}/`:

```
bin/transform-dataset.py air.mon.mean.v501.nc public/data/1980-2010/tiles/temperature-avg air 1980 2010
bin/transform-dataset.py air.mon.mean.v501.nc public/data/1980-2010/tiles/temperature-avg-01 air 1980 2010 1
...

bin/transform-dataset.py precip.mon.total.v501.nc public/data/1980-2010/tiles/precipitation precip 1980 2010
bin/transform-dataset.py precip.mon.total.v501.nc public/data/1980-2010/tiles/precipitation-01 precip 1980 2010 1
...
```
