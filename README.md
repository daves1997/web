# Web Site for TransportForecastAccuracy.com

## GTFS Route Extraction Script

The `scripts/filter_gtfs_route.py` script extracts all GTFS records relevant to a single `route_id` from an input GTFS zip file and writes them to a new GTFS zip. This can be useful for creating a smaller feed focused on one route.

### Usage

```bash
python3 scripts/filter_gtfs_route.py INPUT_GTFS.zip ROUTE_ID OUTPUT_GTFS.zip
```

The output zip will contain the standard GTFS files (agency, stops, routes, trips, stop_times, shapes, calendar and calendar_dates if present) filtered to only include data related to the specified route.
