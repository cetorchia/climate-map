# Installation

Use npm to build the javascript output.

```
npm run build
```

# Important notes

* Coordinates in OSM and geoJSON are `[longitude, latitude]`, but coordinates
in netCDF4 and the transformation code are `[latitude, longitude]`. Make sure
which is which in every case.

# Data source(s)

* [ESRL : PSD : All Gridded Datasets](https://www.esrl.noaa.gov/psd/data/gridded/)

# Data transformation

You can transform the data from the NOAA using `transform-netcdf.py`.
This data transformation script is used to process the netCDF4 files into
various formats so that the web application can read the climate data from
the server.

The script takes input file and output file as arguments. The script will detect
the desired format based on the output file extension.

University of Delaware gridded temperature and precipitation data can be used
for this purpose, but other datasets may be used as well if they are in
netCDF4 format and are grouped by month.

## Transforming to PNG files

These files are used to overlay a PNG representation of the climate data
on the map. This can allow the browser to render colours for different temperatures
or precipitation much quicker than plotting polygons for data it would have to load.

```
# Generate temperature datasets
bin/transform-netcdf.py air.mon.mean.v501.nc public/data/1980-2010/temperature.png air 1980 2010
bin/transform-netcdf.py air.mon.mean.v501.nc public/data/1980-2010/temperature-01.png air 1980 2010 1
bin/transform-netcdf.py air.mon.mean.v501.nc public/data/1980-2010/temperature-02.png air 1980 2010 1
...
bin/transform-netcdf.py air.mon.mean.v501.nc public/data/1980-2010/temperature-12.png air 1980 2010 12

# Generate precipitation datasets
bin/transform-netcdf.py precip.mon.total.v501.nc public/data/1980-2010/precipitation.png precip 1980 2010
bin/transform-netcdf.py precip.mon.total.v501.nc public/data/1980-2010/precipitation-01.png precip 1980 2010 1
bin/transform-netcdf.py precip.mon.total.v501.nc public/data/1980-2010/precipitation-02.png precip 1980 2010 2
...
bin/transform-netcdf.py precip.mon.total.v501.nc public/data/1980-2010/precipitation-12.png precip 1980 2010 12
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
bin/transform-netcdf.py air.mon.mean.v501.nc public/data/1980-2010/ air 1980 2010
bin/transform-netcdf.py air.mon.mean.v501.nc public/data/1980-2010/ air 1980 2010 1
bin/transform-netcdf.py air.mon.mean.v501.nc public/data/1980-2010/ air 1980 2010 2
...
bin/transform-netcdf.py air.mon.mean.v501.nc public/data/1980-2010/ air 1980 2010 12

# Generate precipitation datasets
bin/transform-netcdf.py precip.mon.total.v501.nc public/data/1980-2010/ precip 1980 2010
bin/transform-netcdf.py precip.mon.total.v501.nc public/data/1980-2010/ precip 1980 2010 1
bin/transform-netcdf.py precip.mon.total.v501.nc public/data/1980-2010/ precip 1980 2010 2
...
bin/transform-netcdf.py precip.mon.total.v501.nc public/data/1980-2010/ precip 1980 2010 12
```

The following script does each month in one command for convenience.

```
bin/transform-all-months.sh ~/Documents/Climate/air.mon.mean.v501.nc 1970 2000
bin/transform-all-months.sh ~/Documents/Climate/air.mon.mean.v501.nc 1980 2010
...
```

## Transforming to bulk JSON files

These files individually contain data for all coordinates, and as such the files
can be very large and inefficient for the web application to load.

```
# Generate temperature datasets
bin/transform-netcdf.py air.mon.mean.v501.nc public/data/1980-2010/temperature.json air 1980 2010
bin/transform-netcdf.py air.mon.mean.v501.nc public/data/1980-2010/temperature-01.json air 1980 2010 1
bin/transform-netcdf.py air.mon.mean.v501.nc public/data/1980-2010/temperature-02.json air 1980 2010 2
...

# Generate precipitation datasets
bin/transform-netcdf.py precip.mon.total.v501.nc public/data/1980-2010/precipitation.json precip 1980 2010
bin/transform-netcdf.py precip.mon.total.v501.nc public/data/1980-2010/precipitation-01.json precip 1980 2010 1
bin/transform-netcdf.py precip.mon.total.v501.nc public/data/1980-2010/precipitation-02.json precip 1980 2010 2
...
```
