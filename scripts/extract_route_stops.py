import argparse
import csv
import zipfile
from io import TextIOWrapper


def extract_route_stops(gtfs_zip, route_id):
    """Return list of (stop_id, stop_name) for the given route_id."""
    with zipfile.ZipFile(gtfs_zip) as zf:
        # Gather all trip_ids for the specified route
        with zf.open('trips.txt') as trips_file:
            reader = csv.DictReader(TextIOWrapper(trips_file, encoding='utf-8-sig'))
            trip_ids = {row['trip_id'] for row in reader if row['route_id'] == route_id}

        # Collect all stop_ids from stop_times associated with those trips
        with zf.open('stop_times.txt') as stop_times_file:
            reader = csv.DictReader(TextIOWrapper(stop_times_file, encoding='utf-8-sig'))
            stop_ids = {row['stop_id'] for row in reader if row['trip_id'] in trip_ids}

        # Map stop_id -> stop_name
        stops = []
        with zf.open('stops.txt') as stops_file:
            reader = csv.DictReader(TextIOWrapper(stops_file, encoding='utf-8-sig'))
            for row in reader:
                sid = row['stop_id']
                if sid in stop_ids:
                    stops.append((sid, row['stop_name']))

    # Sort results by stop_id for stable output
    return sorted(stops, key=lambda x: x[0])


def main():
    parser = argparse.ArgumentParser(
        description="Extract stop ids and names for a specific route from a GTFS zip file")
    parser.add_argument('gtfs_zip', help='Path to GTFS zip file')
    parser.add_argument('route_id', help='Route ID to extract stops for')
    args = parser.parse_args()

    stops = extract_route_stops(args.gtfs_zip, args.route_id)
    for sid, name in stops:
        print(f"{sid}, {name}")


if __name__ == '__main__':
    main()

