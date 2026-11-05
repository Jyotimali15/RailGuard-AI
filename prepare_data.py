"""
RailGuard AI - Data preparation.

Turns the raw project dataset (data/dataset_for_project.csv) into the clean file the
app loads into SQLite (data/train_platforms.csv).

Raw columns:
  train_number, train_name, source_station, destination_station, station_name,
  departure_time, passenger_platform, platform_crowded, train_arrival_platform
"""
import csv
import os
import re
from collections import defaultdict

from risk_engine import base_walk_for_station

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
RAW_CSV = os.path.join(DATA_DIR, 'dataset_for_project.csv')
CLEAN_CSV = os.path.join(DATA_DIR, 'train_platforms.csv')

CLEAN_COLUMNS = ['train_number', 'train_name', 'source_station', 'destination_station',
                 'station', 'departure_time', 'platform', 'walk_minutes', 'crowd_level']


def platform_number(text) -> int:
    """'Platform 3' -> 3 ; '3' -> 3"""
    m = re.search(r'\d+', str(text))
    if not m:
        raise ValueError(f'No platform number in {text!r}')
    return int(m.group())


def norm_time(text) -> str:
    """'0:25' -> '00:25'"""
    h, m = str(text).strip().split(':')[:2]
    h, m = int(h), int(m)
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ValueError(f'Bad time {text!r}')
    return f'{h:02d}:{m:02d}'


def crowd_label(value) -> str:
    return 'High' if str(value).strip().lower() in ('yes', 'y', 'true', '1', 'high') else 'Low'


def read_raw(path=RAW_CSV):
    with open(path, 'r', encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def station_sizes(rows):
    """Largest platform number seen per station -> proxy for station size."""
    size = defaultdict(int)
    for r in rows:
        st = r['station_name'].strip().upper()
        size[st] = max(size[st],
                       platform_number(r['passenger_platform']),
                       platform_number(r['train_arrival_platform']))
    return size


def clean_rows(rows, sizes=None):
    """Raw dataset rows -> clean rows (deduplicated on train_number + station)."""
    sizes = sizes or station_sizes(rows)
    seen, out = set(), []
    for r in rows:
        try:
            station = r['station_name'].strip()
            key = (r['train_number'].strip(), station.upper())
            if key in seen:
                continue
            seen.add(key)
            out.append({
                'train_number': r['train_number'].strip(),
                'train_name': r['train_name'].strip(),
                'source_station': r['source_station'].strip(),
                'destination_station': r['destination_station'].strip(),
                'station': station,
                'departure_time': norm_time(r['departure_time']),
                'platform': platform_number(r['train_arrival_platform']),
                'walk_minutes': base_walk_for_station(sizes.get(station.upper(), 4)),
                'crowd_level': crowd_label(r['platform_crowded']),
            })
        except (KeyError, ValueError) as e:
            print(f'[SKIP] bad row {r}: {e}')
    return out


def main():
    rows = read_raw()
    cleaned = clean_rows(rows)
    with open(CLEAN_CSV, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=CLEAN_COLUMNS)
        w.writeheader()
        w.writerows(cleaned)
    print(f'[OK] {len(rows)} raw rows -> {len(cleaned)} clean rows -> {CLEAN_CSV}')


if __name__ == '__main__':
    main()
