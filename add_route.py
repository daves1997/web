import argparse
import csv
import os
import shutil
import tempfile
import zipfile
from datetime import timedelta


def parse_ids(value):
    return [v.strip() for v in value.split(',') if v.strip()]


def parse_travel_times(value):
    return [int(v) for v in value.split(',') if v.strip()]


def parse_frequencies(value):
    result = []
    for part in value.split(';'):
        part = part.strip()
        if not part:
            continue
        start, end, headway = part.split('-')
        result.append((start, end, int(headway)))
    return result


def hhmmss(seconds):
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def add_route(args):
    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(args.gtfs_zip) as zf:
            zf.extractall(tmpdir)

        routes_file = os.path.join(tmpdir, 'routes.txt')
        with open(routes_file, newline='') as f:
            reader = csv.DictReader(f)
            routes = list(reader)
            route_fields = reader.fieldnames
        new_route = {k: '' for k in route_fields}
        if 'route_id' in route_fields:
            new_route['route_id'] = args.route_id
        if 'route_short_name' in route_fields:
            new_route['route_short_name'] = args.route_name
        if 'route_long_name' in route_fields and 'route_short_name' not in route_fields:
            new_route['route_long_name'] = args.route_name
        if 'route_type' in route_fields:
            new_route['route_type'] = args.route_type
        routes.append(new_route)
        with open(routes_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=route_fields)
            writer.writeheader()
            writer.writerows(routes)

        trips_file = os.path.join(tmpdir, 'trips.txt')
        with open(trips_file, newline='') as f:
            reader = csv.DictReader(f)
            trips = list(reader)
            trips_fields = reader.fieldnames
        for trip_id, service_id in zip(args.trip_ids, args.service_ids):
            row = {k: '' for k in trips_fields}
            if 'route_id' in trips_fields:
                row['route_id'] = args.route_id
            if 'service_id' in trips_fields:
                row['service_id'] = service_id
            if 'trip_id' in trips_fields:
                row['trip_id'] = trip_id
            if 'direction_id' in trips_fields:
                row['direction_id'] = '0'
            trips.append(row)
            if args.bidirectional:
                rev = {**row}
                rev['trip_id'] = f"{trip_id}_rev"
                if 'direction_id' in trips_fields:
                    rev['direction_id'] = '1'
                trips.append(rev)
        with open(trips_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=trips_fields)
            writer.writeheader()
            writer.writerows(trips)

        stop_times_file = os.path.join(tmpdir, 'stop_times.txt')
        with open(stop_times_file, newline='') as f:
            reader = csv.DictReader(f)
            stop_times = list(reader)
            st_fields = reader.fieldnames

        def build_stop_time_rows(tid, stops):
            rows = []
            acc = 0
            for idx, stop in enumerate(stops):
                row = {k: '' for k in st_fields}
                if 'trip_id' in st_fields:
                    row['trip_id'] = tid
                if 'stop_id' in st_fields:
                    row['stop_id'] = stop
                if 'stop_sequence' in st_fields:
                    row['stop_sequence'] = str(idx + 1)
                if 'arrival_time' in st_fields:
                    row['arrival_time'] = hhmmss(acc)
                if 'departure_time' in st_fields:
                    row['departure_time'] = hhmmss(acc)
                rows.append(row)
                if idx < len(args.travel_times):
                    acc += args.travel_times[idx]
            return rows

        for trip_id, _ in zip(args.trip_ids, args.service_ids):
            stop_times.extend(build_stop_time_rows(trip_id, args.stop_sequence))
            if args.bidirectional:
                rev_seq = list(reversed(args.stop_sequence))
                stop_times.extend(build_stop_time_rows(f"{trip_id}_rev", rev_seq))

        with open(stop_times_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=st_fields)
            writer.writeheader()
            writer.writerows(stop_times)

        freq_file = os.path.join(tmpdir, 'frequencies.txt')
        if os.path.exists(freq_file):
            with open(freq_file, newline='') as f:
                reader = csv.DictReader(f)
                freqs = list(reader)
                freq_fields = reader.fieldnames
        else:
            freq_fields = ['trip_id', 'start_time', 'end_time', 'headway_secs', 'exact_times']
            freqs = []
        for trip_id, _ in zip(args.trip_ids, args.service_ids):
            for start, end, headway in args.frequencies:
                row = {k: '' for k in freq_fields}
                row['trip_id'] = trip_id
                row['start_time'] = start
                row['end_time'] = end
                row['headway_secs'] = str(headway)
                row['exact_times'] = row.get('exact_times', '0') or '0'
                freqs.append(row)
            if args.bidirectional:
                for start, end, headway in args.frequencies:
                    row = {k: '' for k in freq_fields}
                    row['trip_id'] = f"{trip_id}_rev"
                    row['start_time'] = start
                    row['end_time'] = end
                    row['headway_secs'] = str(headway)
                    row['exact_times'] = row.get('exact_times', '0') or '0'
                    freqs.append(row)
        with open(freq_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=freq_fields)
            writer.writeheader()
            writer.writerows(freqs)

        out_base = args.gtfs_zip[:-4] if args.gtfs_zip.endswith('.zip') else args.gtfs_zip
        out_zip = f"{out_base}_modified.zip"
        shutil.make_archive(out_base + '_modified', 'zip', tmpdir)
        print(f"Modified GTFS written to {out_zip}")


def main():
    parser = argparse.ArgumentParser(description="Add a route to a GTFS zip file")
    parser.add_argument('gtfs_zip', help='Path to GTFS zip file')
    parser.add_argument('--route_name', required=True)
    parser.add_argument('--route_id', required=True)
    parser.add_argument('--route_type', required=True)
    parser.add_argument('--trip_ids', required=True, help='Comma separated trip IDs')
    parser.add_argument('--service_ids', required=True, help='Comma separated service IDs')
    parser.add_argument('--stop_sequence', required=True, help='Comma separated stop IDs')
    parser.add_argument('--travel_times', required=True, help='Comma separated travel times in seconds')
    parser.add_argument('--frequencies', required=True, help='Semicolon separated start-end-headway entries')
    parser.add_argument('--bidirectional', action='store_true', help='Create reverse trips as well')

    args = parser.parse_args()
    args.trip_ids = parse_ids(args.trip_ids)
    args.service_ids = parse_ids(args.service_ids)
    if len(args.trip_ids) != len(args.service_ids):
        parser.error('Number of trip_ids must equal number of service_ids')
    args.stop_sequence = parse_ids(args.stop_sequence)
    args.travel_times = parse_travel_times(args.travel_times)
    if len(args.travel_times) != len(args.stop_sequence) - 1:
        parser.error('Need one less travel_time than number of stops')
    args.frequencies = parse_frequencies(args.frequencies)

    add_route(args)


if __name__ == '__main__':
    main()
