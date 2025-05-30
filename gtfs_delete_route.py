import argparse
import csv
import io
import zipfile


def read_csv_from_zip(zf, name):
    """Return (rows, fieldnames) for CSV file in a ZipFile."""
    try:
        with zf.open(name) as f:
            content = f.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(content))
        return list(reader), reader.fieldnames
    except KeyError:
        return None, None


def write_csv_to_string(rows, fieldnames):
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator='\n')
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return output.getvalue()


def delete_route(input_zip_path, output_zip_path, route_id):
    with zipfile.ZipFile(input_zip_path, 'r') as zf:
        file_names = zf.namelist()
        data = {}
        headers = {}
        for name in file_names:
            rows, header = read_csv_from_zip(zf, name)
            if rows is not None:
                data[name] = rows
                headers[name] = header

    if 'routes.txt' not in data:
        raise ValueError('routes.txt not found in GTFS data')

    # Remove matching routes
    data['routes.txt'] = [r for r in data['routes.txt'] if r.get('route_id') != route_id]

    # Identify trips to remove
    trips = data.get('trips.txt', [])
    removed_trip_ids = [t['trip_id'] for t in trips if t.get('route_id') == route_id]
    removed_service_ids = set(t['service_id'] for t in trips if t.get('route_id') == route_id)
    data['trips.txt'] = [t for t in trips if t.get('route_id') != route_id]

    # Remove stop_times referencing removed trips
    stop_times = data.get('stop_times.txt', [])
    data['stop_times.txt'] = [st for st in stop_times if st.get('trip_id') not in removed_trip_ids]

    # Determine which stops are still referenced
    referenced_stops = set(st['stop_id'] for st in data['stop_times.txt'])
    stops = data.get('stops.txt', [])
    data['stops.txt'] = [s for s in stops if s.get('stop_id') in referenced_stops]

    # Remove calendar entries for unused service_ids
    remaining_service_ids = set(t['service_id'] for t in data.get('trips.txt', []))
    obsolete_services = removed_service_ids - remaining_service_ids

    if 'calendar.txt' in data:
        data['calendar.txt'] = [c for c in data['calendar.txt'] if c.get('service_id') not in obsolete_services]
    if 'calendar_dates.txt' in data:
        data['calendar_dates.txt'] = [c for c in data['calendar_dates.txt'] if c.get('service_id') not in obsolete_services]

    # Remove shapes not referenced by any trips
    if 'shapes.txt' in data and 'trips.txt' in data:
        remaining_shape_ids = set(t['shape_id'] for t in data['trips.txt'] if 'shape_id' in t and t['shape_id'])
        data['shapes.txt'] = [s for s in data['shapes.txt'] if s.get('shape_id') in remaining_shape_ids]

    # Write everything back to a new zip file
    with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as out_zip:
        for name, rows in data.items():
            fieldnames = headers.get(name)
            if not fieldnames:
                continue
            csv_content = write_csv_to_string(rows, fieldnames)
            out_zip.writestr(name, csv_content)


def main():
    parser = argparse.ArgumentParser(description="Remove a route and related data from a GTFS zip file")
    parser.add_argument('input_zip', help='Path to input GTFS zip file')
    parser.add_argument('route_id', help='Route ID to remove')
    parser.add_argument('output_zip', help='Path to output GTFS zip file')
    args = parser.parse_args()

    delete_route(args.input_zip, args.output_zip, args.route_id)


if __name__ == '__main__':
    main()
