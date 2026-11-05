"""
RailGuard AI - ML Training Dataset Generator (built from the real project dataset)

Every record in data/dataset_for_project.csv gives a real platform gap
(passenger_platform vs train_arrival_platform), a real crowd flag and a real station.
The one thing the CSV cannot tell us is "how many minutes were left", so we sample
several plausible values per record. Labels come from risk_engine.classify_risk.

Output: data/risk_training_dataset.csv
"""
import csv
import os
import random

from prepare_data import read_raw, station_sizes, platform_number
from risk_engine import base_walk_for_station, classify_risk

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
OUTPUT_CSV = os.path.join(BASE_DIR, 'data', 'risk_training_dataset.csv')

SAMPLES_PER_RECORD = 5          # 3568 records x 5 = 17,840 training rows
random.seed(42)                 # reproducible

HEADERS = ['minutes_remaining', 'platform_gap', 'base_walk_minutes', 'crowded',
           'estimated_walk_minutes', 'time_buffer_margin', 'risk_label']


def generate_dataset():
    rows = read_raw()
    sizes = station_sizes(rows)
    records = []

    for r in rows:
        gap = abs(platform_number(r['passenger_platform']) - platform_number(r['train_arrival_platform']))
        crowded = 1 if r['platform_crowded'].strip().lower() == 'yes' else 0
        base_walk = base_walk_for_station(sizes[r['station_name'].strip().upper()])

        for _ in range(SAMPLES_PER_RECORD):
            minutes_remaining = random.randint(2, 60)
            label, walk, buffer_ = classify_risk(minutes_remaining, gap, base_walk, crowded)
            records.append([minutes_remaining, gap, base_walk, crowded, walk, buffer_, label])

    random.shuffle(records)
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(HEADERS)
        w.writerows(records)

    counts = {}
    for rec in records:
        counts[rec[-1]] = counts.get(rec[-1], 0) + 1
    print(f'[OK] {len(records)} training rows -> {OUTPUT_CSV}')
    print(f'     label distribution: {counts}')


if __name__ == '__main__':
    generate_dataset()
