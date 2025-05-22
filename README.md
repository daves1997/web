# Web Site for TransportForecastAccuracy.com

This repository also contains utility scripts used for working with GTFS data.

## Extracting stops for a route

The `scripts/extract_route_stops.py` script can be used to list all stops
belonging to a specific route ID within a GTFS zip file.

Example usage:

```bash
python scripts/extract_route_stops.py path/to/gtfs.zip ROUTE_ID
```

The script outputs the stop ID and stop name for each stop found.
