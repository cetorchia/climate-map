# Using Map Tiles

This document shall describe approaches to using different kinds of map
tiles underneath your climate map colouring tiles.

You can use both raster tiles and vector tilesets, but for vector tiles
you need Mapbox GL. If you use raster tiles you probably want to remove
mapbox-gl from the node packages as it is quite large.

## Configuring tilesets

The `config/config.json` file allows you to configure where map tiles will
be read from. The `config.json.example` uses a basic OpenStreetMap reference.

OpenStreetMap's tile URL ends in PNG, so it is a raster tileset. Vector tilesets
will end with PBF or MVT. Since these are not image formats, the URL pointing
to the tileset will actually be a style JSON file that will be used to render
the vector tiles.

### Mapbox GL configuration

Mapbox GL is a javascript library that lets you render vector tiles on your map.
These are supposedly more efficient than raster tiles, though IMO they are
worse because they require more resources on the user's device but less
bandwidth is used.

First install the following node packages:

```
npm install mapbox-gl
npm install mapbox-gl-leaflet
```

Uncommon the following lines in `js/main.js`:

```
/* Enable this if you want to use mapboxGL */
//await import(/* webpackChunkName: "mapbox-gl-leaflet" */ 'mapbox-gl-leaflet');
//await import('mapbox-gl/dist/mapbox-gl.css');
```

Set up `config.json` with a mapboxGL tile layer similar to the following:

```
{
    "min_zoom": 2,
    "max_zoom": 10,
    "search_zoom": 7,
    "climate_tile_layer": {
        "z_index": 2,
        "url": "/tiles/climate",
        "opacity": 0.5,
        "format": "png"
    },
    "tile_layers": [
        {
            "mapboxGL": true,
            "style_url": "https://api.maptiler.com/maps/{mapId}/style.json?key={key}",
            "access_token": "{access_token}",
            "attribution": "<a href=\"https://www.maptiler.com/copyright/\" target=\"_blank\">MapTiler</a>, <a href=\"https://www.openstreetmap.org/copyright\" target=\"_blank\">OpenStreetMap</a>",
            "z_index": 1
        },
        "contact": {
            "support": {
                "username": "support",
                "domain": "myclimatemap.org"
            }
        }
    ]
}
```

The `mapboxGL` attribute tells the javascript code to create a mapbox GL layer
instead of a regular tile layer.

## Generating your own map tiles

You can, of course, generate your own map tiles such as OpenStreetMap or
Natural Earth Data.

Natural Earth Data is actually a good choice because, in my opinion, you don't
need very detailed objects on the map.

Install the following package(s):

```
python3-mapnik
```

To generate map tiles for zoom levels 0 through 8, run:

```
bin/generate-map-tiles.py 0 8
```

This will download all the Natural Earth Data and use mapnik to generate
many zoom levels of tiles. This will put tiles in `public/map-tiles`.
Then specify this `config.json`:

```
    "tile_layers": [
        {
            "url": "/map-tiles/{z}/{x}/{y}.jpeg",
            "attribution": "<a href=\"https://www.naturalearthdata.com/\">Natural Earth Data</a>",
            "z_index": 1,
            "max_zoom": 8
        }
    ],
```
