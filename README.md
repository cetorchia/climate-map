# Installation

Use npm to build the javascript output.

```
npm run build
```

# Data source(s)

* [ESRL : PSD : All Gridded Datasets](https://www.esrl.noaa.gov/psd/data/gridded/)

# Data transformation

You can transform the data from the NOAA using `transform-netcdf.py`

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

University of Delaware gridded temperature and precipitation data can be used
for this purpose, but other datasets may be used as well if they are in
netCDF4 format and are grouped by month.
