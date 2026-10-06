# Vendored basemap

`world_110m.json` is the plotly.js world topojson, downloaded unchanged on 2026-10-01 from
https://cdn.plot.ly/un/world_110m.json, the file plotly.js requests at view time for a
`Scattergeo` with the default scope and resolution. Installed plotly (Python) version: 7.1.0.

`showcase_map.geo_assets_html()` hands it to plotly.js via `window.PlotlyGeoAssets.topojson.world_110m`,
so exported pages need no network. Licence not checked here.
