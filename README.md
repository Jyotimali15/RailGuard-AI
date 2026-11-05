# RailGuard AI - Platform Change Alert System

Passenger picks a train + station and enters the platform they are standing on.
The app compares it with the train's arrival platform:
- same -> "RIGHT PLATFORM"
- different -> "WRONG PLATFORM - change to Platform X", plus walking time and a
  Low / Medium / High risk of missing the train (Random Forest model).

## Run
```
pip install -r requirements.txt
python app.py            # http://127.0.0.1:5000
```
The application initializes its database and loads the trained ML model. To rebuild everything from the dataset:
```
python prepare_data.py          # dataset_for_project.csv -> data/train_platforms.csv
python generate_ml_dataset.py   # -> data/risk_training_dataset.csv (17,840 rows)
python train_model.py           # -> models/risk_model.joblib + model_metrics.json
```
To reseed the database from scratch, delete `data/railguard.db` and start the app.

## Files
| File | Purpose |
|---|---|
| `risk_engine.py` | Risk rules + walk-time formula (single source of truth) |
| `prepare_data.py` | Cleans the raw dataset (platform numbers, HH:MM, crowd Yes/No, station size) |
| `generate_ml_dataset.py` | Builds ML training rows from real platform gaps/crowd in the dataset |
| `train_model.py` | Trains + evaluates the Random Forest |
| `app.py` | Flask app, API, admin panel |
| `templates/`, `static/` | Your original passenger + admin pages, with their CSS and JS |

Set `SECRET_KEY` and `ADMIN_PASSWORD` environment variables before any real deployment.

## Using your own dashboard pages
Put your `index.html` and `admin.html` in `templates/` (replace mine). The API keeps all the
old response fields, so old pages keep working. Extra new fields: `alert`, `platform_gap`,
`source_station`, `destination_station`. Users must pick a station (trains stop at many stations).

## Old database
On every start the app adds any missing train stops from `data/train_platforms.csv`
(an old `railguard.db` is upgraded automatically; platforms edited in admin are kept).

## Large datasets
The train box is a searchable dropdown: as the user types a number or name, `/api/search-trains`
returns the best 20 matches, so 1,000 or 100,000 trains work the same (tested: 63,000 stops, ~20 ms).
To use a bigger dataset: replace `data/dataset_for_project.csv`, then run
`python prepare_data.py`, `python generate_ml_dataset.py`, `python train_model.py`,
and start the app (it adds the new trains to the database automatically).
You can also upload the CSV from the admin page.
