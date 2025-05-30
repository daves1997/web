# Web Site for TransportForecastAccuracy.com

## GTFS Route Removal Script

`gtfs_delete_route.py` removes a specified `route_id` and all related data from a GTFS zip archive. Usage:

```bash
python gtfs_delete_route.py input_gtfs.zip ROUTE_ID output_gtfs.zip
```

This writes `output_gtfs.zip` with the route and all associated trips, stop times, stops, and service calendar entries removed.
