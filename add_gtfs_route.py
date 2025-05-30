import argparse
import csv
import json
import os
import shutil
import tempfile
import zipfile


def seconds_to_hms(seconds: int) -> str:
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def read_fieldnames(path: str):
    if os.path.exists(path):
        with open(path, newline='', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            return next(reader)
    return None


def append_row(path: str, row: dict, default_fields=None):
    fields = read_fieldnames(path)
    if fields is None:
        fields = default_fields if default_fields else list(row.keys())
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
    with open(path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writerow(row)


def add_route(temp_dir: str, cfg: dict):
    # routes.txt
    routes_path = os.path.join(temp_dir, 'routes.txt')
    route_row = {
        'route_id': cfg['route_id'],
        'route_short_name': cfg.get('route_short_name', cfg['route_id']),
        'route_long_name': cfg.get('route_name', ''),
        'route_type': cfg.get('route_type', '')
    }
    append_row(routes_path, route_row)

    # trips, stop_times, frequencies
    trips_path = os.path.join(temp_dir, 'trips.txt')
    stop_times_path = os.path.join(temp_dir, 'stop_times.txt')
    freq_path = os.path.join(temp_dir, 'frequencies.txt')

    stops = cfg['stops']
    times = cfg['travel_times']

    for trip in cfg['trips']:
        trip_row = {
            'route_id': cfg['route_id'],
            'service_id': trip['service_id'],
            'trip_id': trip['trip_id'],
            'direction_id': trip.get('direction_id', '0')
        }
        append_row(trips_path, trip_row)
        for idx, stop_id in enumerate(stops):
            arrival = seconds_to_hms(times[idx])
            st_row = {
                'trip_id': trip['trip_id'],
                'arrival_time': arrival,
                'departure_time': arrival,
                'stop_id': stop_id,
                'stop_sequence': idx + 1
            }
            append_row(stop_times_path, st_row)
        if all(k in trip for k in ('start_time', 'end_time', 'headway_secs')):
            freq_row = {
                'trip_id': trip['trip_id'],
                'start_time': trip['start_time'],
                'end_time': trip['end_time'],
                'headway_secs': trip['headway_secs']
            }
            append_row(freq_path, freq_row, ['trip_id', 'start_time', 'end_time', 'headway_secs'])


def main():
    parser = argparse.ArgumentParser(description='Add a route to a GTFS zip file')
    parser.add_argument('input_gtfs', help='Path to existing GTFS zip')
    parser.add_argument('output_gtfs', help='Path for modified GTFS zip')
    parser.add_argument('config', help='JSON file with route information')
    args = parser.parse_args()

    with open(args.config, encoding='utf-8') as f:
        cfg = json.load(f)

    tmp = tempfile.mkdtemp()
    try:
        with zipfile.ZipFile(args.input_gtfs) as zf:
            zf.extractall(tmp)
        add_route(tmp, cfg)
        with zipfile.ZipFile(args.output_gtfs, 'w', zipfile.ZIP_DEFLATED) as zf:
            for fname in os.listdir(tmp):
                zf.write(os.path.join(tmp, fname), arcname=fname)
    finally:
        shutil.rmtree(tmp)


if __name__ == '__main__':
    main()
