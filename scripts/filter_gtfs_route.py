import argparse
import csv
import io
import zipfile
from typing import Dict, List, Iterable

def read_csv_from_zip(zip_file: zipfile.ZipFile, name: str) -> List[Dict[str, str]]:
    if name not in zip_file.namelist():
        return []
    with zip_file.open(name) as f:
        # decode assuming UTF-8
        text = io.TextIOWrapper(f, encoding='utf-8-sig')
        reader = csv.DictReader(text)
        return list(reader)


def write_csv_to_zip(zip_file: zipfile.ZipFile, name: str, rows: Iterable[Dict[str, str]]):
    rows = list(rows)
    if not rows:
        return
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=rows[0].keys())
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    zip_file.writestr(name, output.getvalue())


def filter_gtfs_by_route(input_zip: str, output_zip: str, route_id: str):
    with zipfile.ZipFile(input_zip, 'r') as zin:
        # Read necessary files
        routes = read_csv_from_zip(zin, 'routes.txt')
        trips = read_csv_from_zip(zin, 'trips.txt')
        stop_times = read_csv_from_zip(zin, 'stop_times.txt')
        stops = read_csv_from_zip(zin, 'stops.txt')
        shapes = read_csv_from_zip(zin, 'shapes.txt')
        agency = read_csv_from_zip(zin, 'agency.txt')
        calendar = read_csv_from_zip(zin, 'calendar.txt')
        calendar_dates = read_csv_from_zip(zin, 'calendar_dates.txt')
        frequencies = read_csv_from_zip(zin, 'frequencies.txt')

        # Filter routes
        selected_routes = [r for r in routes if r.get('route_id') == route_id]
        if not selected_routes:
            raise ValueError(f"Route {route_id} not found in routes.txt")
        agency_ids = {r.get('agency_id') for r in selected_routes if r.get('agency_id')}

        # Filter trips
        selected_trips = [t for t in trips if t.get('route_id') == route_id]
        trip_ids = {t.get('trip_id') for t in selected_trips}
        service_ids = {t.get('service_id') for t in selected_trips if t.get('service_id')}
        shape_ids = {t.get('shape_id') for t in selected_trips if t.get('shape_id')}

        # Filter stop_times
        selected_stop_times = [st for st in stop_times if st.get('trip_id') in trip_ids]
        stop_ids = {st.get('stop_id') for st in selected_stop_times}

        # Filter stops
        selected_stops = [s for s in stops if s.get('stop_id') in stop_ids]

        # Filter shapes
        selected_shapes = [sh for sh in shapes if sh.get('shape_id') in shape_ids]

        # Filter agency
        if agency and agency_ids:
            selected_agency = [a for a in agency if a.get('agency_id') in agency_ids]
        else:
            selected_agency = agency

        # Filter calendar
        selected_calendar = [c for c in calendar if c.get('service_id') in service_ids]

        # Filter calendar_dates
        selected_calendar_dates = [c for c in calendar_dates if c.get('service_id') in service_ids]

        # Filter frequencies
        selected_frequencies = [f for f in frequencies if f.get('trip_id') in trip_ids]

        # Start writing output zip
        with zipfile.ZipFile(output_zip, 'w', compression=zipfile.ZIP_DEFLATED) as zout:
            # We maintain the same file order as input if possible
            write_csv_to_zip(zout, 'agency.txt', selected_agency)
            write_csv_to_zip(zout, 'stops.txt', selected_stops)
            write_csv_to_zip(zout, 'routes.txt', selected_routes)
            write_csv_to_zip(zout, 'trips.txt', selected_trips)
            write_csv_to_zip(zout, 'stop_times.txt', selected_stop_times)
            write_csv_to_zip(zout, 'shapes.txt', selected_shapes)
            write_csv_to_zip(zout, 'calendar.txt', selected_calendar)
            write_csv_to_zip(zout, 'calendar_dates.txt', selected_calendar_dates)
            write_csv_to_zip(zout, 'frequencies.txt', selected_frequencies)

            # Copy any other files unchanged
            for name in zin.namelist():
                if name in {
                    'agency.txt', 'stops.txt', 'routes.txt', 'trips.txt',
                    'stop_times.txt', 'shapes.txt', 'calendar.txt',
                    'calendar_dates.txt', 'frequencies.txt'
                }:
                    continue
                zout.writestr(name, zin.read(name))


def main():
    parser = argparse.ArgumentParser(description='Extract a single route from a GTFS zip file.')
    parser.add_argument('input_zip', help='Path to the input GTFS zip file')
    parser.add_argument('route_id', help='Route ID to extract')
    parser.add_argument('output_zip', help='Path for the output GTFS zip file')
    args = parser.parse_args()
    filter_gtfs_by_route(args.input_zip, args.output_zip, args.route_id)


if __name__ == '__main__':
    main()
