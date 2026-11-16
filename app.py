"""
RailGuard AI - Railway Platform Change Alert & Risk Analysis System
Flask backend (uses the project dataset: data/dataset_for_project.csv)
"""

import csv
import json
import os
import sqlite3
from datetime import datetime, timedelta

from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash

from prepare_data import clean_rows, CLEAN_CSV
from risk_engine import classify_risk

app = Flask(__name__)
@app.route('/sitemap.xml')
def sitemap():
    return send_from_directory(
        os.path.dirname(os.path.abspath(__file__)),
        'sitemap.xml',
        mimetype='application/xml'
    )
app.secret_key = os.environ.get('SECRET_KEY', 'railguard_secret_capstone_2026')
@app.route('/service-worker.js')
def service_worker():
    return send_from_directory(
        app.static_folder,
        'service-worker.js',
        mimetype='application/javascript'
    )

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DB_PATH = os.path.join(DATA_DIR, 'railguard.db')
MODELS_DIR = os.path.join(BASE_DIR, 'models')
MODEL_FILE = os.path.join(MODELS_DIR, 'risk_model.joblib')
METRICS_FILE = os.path.join(MODELS_DIR, 'model_metrics.json')

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)

ml_model = None

DEFAULT_ADMIN_USER = 'admin'
DEFAULT_ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')


def load_ml_model():
    """Load the scikit-learn model if models/risk_model.joblib exists."""
    global ml_model
    if os.path.exists(MODEL_FILE):
        try:
            import joblib
            ml_model = joblib.load(MODEL_FILE)
            print('[INFO] Loaded Random Forest model.')
        except Exception as e:
            print(f'[WARN] Could not load ML model: {e}')
            ml_model = None
    else:
        print('[INFO] No model file yet - using the rule-based engine. Run: python train_model.py')


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


UPSERT_SQL = '''
    INSERT INTO trains (train_number, train_name, source_station, destination_station,
                        station, platform, departure_time, walk_minutes, crowd_level, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    ON CONFLICT(train_number, station) DO UPDATE SET
        train_name = excluded.train_name,
        source_station = excluded.source_station,
        destination_station = excluded.destination_station,
        platform = excluded.platform,
        departure_time = excluded.departure_time,
        walk_minutes = excluded.walk_minutes,
        crowd_level = excluded.crowd_level,
        updated_at = CURRENT_TIMESTAMP
'''


def upsert_clean_rows(cursor, rows):
    for r in rows:
        cursor.execute(UPSERT_SQL, (r['train_number'], r['train_name'], r['source_station'],
                                    r['destination_station'], r['station'], r['platform'],
                                    r['departure_time'], r['walk_minutes'], r['crowd_level']))


def init_db():
    """Create tables (migrating older DBs) and seed from data/train_platforms.csv."""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS trains (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            train_number TEXT NOT NULL,
            train_name TEXT NOT NULL,
            source_station TEXT DEFAULT '',
            destination_station TEXT DEFAULT '',
            station TEXT NOT NULL,
            station_code TEXT DEFAULT '',
            platform INTEGER NOT NULL,
            departure_time TEXT NOT NULL,
            walk_minutes INTEGER NOT NULL DEFAULT 5,
            crowd_level TEXT NOT NULL DEFAULT 'Low',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(train_number, station)
        )
    ''')
    # Migrate a database created by the older version of the app
    existing = {row['name'] for row in cur.execute('PRAGMA table_info(trains)')}
    for col in ('source_station', 'destination_station', 'station_code'):
        if col not in existing:
            cur.execute(f"ALTER TABLE trains ADD COLUMN {col} TEXT DEFAULT ''")

    cur.execute('CREATE INDEX IF NOT EXISTS idx_trains_number ON trains(train_number)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_trains_name ON trains(train_name COLLATE NOCASE)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_trains_station ON trains(station COLLATE NOCASE)')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')
    cur.execute('SELECT id FROM admins WHERE username = ?', (DEFAULT_ADMIN_USER,))
    if not cur.fetchone():
        cur.execute('INSERT INTO admins (username, password_hash) VALUES (?, ?)',
                    (DEFAULT_ADMIN_USER, generate_password_hash(DEFAULT_ADMIN_PASSWORD)))

    # Sync the project dataset on every start. INSERT OR IGNORE adds missing trains
    # (even into an old database) but never overwrites platforms changed by the admin.
    if not os.path.exists(CLEAN_CSV):
        import prepare_data
        prepare_data.main()
    with open(CLEAN_CSV, 'r', encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    before = cur.execute('SELECT COUNT(*) FROM trains').fetchone()[0]
    cur.executemany('''INSERT OR IGNORE INTO trains
        (train_number, train_name, source_station, destination_station, station,
         platform, departure_time, walk_minutes, crowd_level)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        [(r['train_number'], r['train_name'], r['source_station'], r['destination_station'],
          r['station'], int(r['platform']), r['departure_time'], int(r['walk_minutes']),
          r['crowd_level']) for r in rows])
    after = cur.execute('SELECT COUNT(*) FROM trains').fetchone()[0]
    print(f'[INFO] Dataset sync: {after - before} new train stops added ({after} total).')

    conn.commit()
    conn.close()


def calculate_minutes_remaining(departure_time_str):
    """
    Minutes until the HH:MM departure. For demos at odd hours, a gap above 3 hours
    is folded into a realistic 15-75 minute window (the UI also has a manual override).
    """
    try:
        now = datetime.now()
        h, m = map(int, departure_time_str.split(':'))
        dep = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if dep < now:
            dep += timedelta(days=1)
        minutes = int((dep - now).total_seconds() // 60)
        if minutes > 180:
            minutes = (minutes % 60) + 15
        return max(5, minutes)
    except Exception:
        return 25


# ------------------------ Localised text ------------------------

def build_summary(is_match, risk_level, assigned, walk, minutes, crowd, lang):
    crowd_word = {'en': {'High': 'crowded', 'Low': 'clear'},
                  'hi': {'High': 'भीड़भाड़ वाले', 'Low': 'खाली'},
                  'mr': {'High': 'गर्दीच्या', 'Low': 'मोकळ्या'}}[lang][crowd]
    if is_match:
        return {'en': 'You are already on the correct platform. No change needed.',
                'hi': 'आप पहले से ही सही प्लेटफॉर्म पर हैं। बदलने की आवश्यकता नहीं है।',
                'mr': 'तुम्ही आधीच योग्य प्लॅटफॉर्मवर आहात. बदलण्याची गरज नाही.'}[lang]
    if risk_level == 'High':
        return {'en': f'CRITICAL: Train arrives on Platform {assigned}. Only {minutes} min left for a ~{walk} min walk through a {crowd_word} platform!',
                'hi': f'अति आवश्यक: ट्रेन प्लेटफॉर्म {assigned} पर आएगी। {crowd_word} प्लेटफॉर्म पर ~{walk} मिनट चलने के लिए केवल {minutes} मिनट शेष हैं!',
                'mr': f'अतिशय गंभीर: गाडी प्लॅटफॉर्म {assigned} वर येईल. {crowd_word} प्लॅटफॉर्मवर ~{walk} मिनिटे चालण्यासाठी केवळ {minutes} मिनिटे शिल्लक!'}[lang]
    if risk_level == 'Medium':
        return {'en': f'CAUTION: Platform changed to {assigned}. Time is tight ({minutes} min) for a ~{walk} min walk.',
                'hi': f'सावधानी: प्लेटफॉर्म {assigned} हो गया है। ~{walk} मिनट की दूरी के लिए समय सीमित ({minutes} मिनट) है।',
                'mr': f'सावधगिरी: प्लॅटफॉर्म {assigned} झाला आहे. ~{walk} मिनिटांच्या अंतरासाठी वेळ मर्यादित ({minutes} मिनिटे) आहे.'}[lang]
    return {'en': f'MANAGEABLE: Go to Platform {assigned}. You have {minutes} min for a ~{walk} min walk.',
            'hi': f'सुरक्षित: प्लेटफॉर्म {assigned} पर जाएं। ~{walk} मिनट चलने के लिए {minutes} मिनट शेष हैं।',
            'mr': f'सुरक्षित: प्लॅटफॉर्म {assigned} वर जा. ~{walk} मिनिटे चालण्यासाठी {minutes} मिनिटे शिल्लक आहेत.'}[lang]


def build_alert(is_match, current, assigned, lang):
    """The headline 'right platform / change platform' alert (core idea of the project)."""
    if is_match:
        return {'en': f'RIGHT PLATFORM - your train arrives on Platform {assigned}.',
                'hi': f'सही प्लेटफॉर्म - आपकी ट्रेन प्लेटफॉर्म {assigned} पर आएगी।',
                'mr': f'योग्य प्लॅटफॉर्म - तुमची गाडी प्लॅटफॉर्म {assigned} वर येईल.'}[lang]
    return {'en': f'WRONG PLATFORM - change from Platform {current} to Platform {assigned}.',
            'hi': f'गलत प्लेटफॉर्म - प्लेटफॉर्म {current} से प्लेटफॉर्म {assigned} पर जाएं।',
            'mr': f'चुकीचा प्लॅटफॉर्म - प्लॅटफॉर्म {current} वरून प्लॅटफॉर्म {assigned} वर जा.'}[lang]


def generate_guidance_steps(is_match, current, assigned, walk, lang):
    if is_match:
        return {'en': [f'You are on the assigned Platform {assigned}.',
                       'Check your coach position on the overhead indicator.',
                       'Stand behind the yellow safety line until the train stops.'],
                'hi': [f'आप सही प्लेटफॉर्म {assigned} पर हैं।',
                       'ओवरहेड इंडिकेटर पर अपने कोच की स्थिति देखें।',
                       'ट्रेन रुकने तक पीली सुरक्षा रेखा के पीछे खड़े रहें।'],
                'mr': [f'तुम्ही योग्य प्लॅटफॉर्म {assigned} वर आहात.',
                       'ओव्हरहेड इंडिकेटरवर आपल्या डब्याची स्थिती तपासा.',
                       'गाडी थांबेपर्यंत पिवळ्या सुरक्षा रेषेच्या मागे उभे राहा.']}[lang]
    return {'en': [f'Head to the nearest foot overbridge (FOB), lift or escalator on Platform {current}.',
                   f'Cross over to Platform {assigned} (about {walk} min walk).',
                   f'At Platform {assigned}, confirm your coach position on the display.'],
            'hi': [f'प्लेटफॉर्म {current} पर सबसे नज़दीकी पैदल पुल (FOB), लिफ्ट या एस्केलेटर की ओर बढ़ें।',
                   f'प्लेटफॉर्म {assigned} की ओर जाएं (लगभग {walk} मिनट)।',
                   f'प्लेटफॉर्म {assigned} पर पहुंचकर डिस्प्ले बोर्ड पर कोच की स्थिति देखें।'],
            'mr': [f'प्लॅटफॉर्म {current} वरील जवळच्या पादचारी पुलाकडे (FOB), लिफ्ट किंवा एस्कलेटरकडे जा.',
                   f'प्लॅटफॉर्म {assigned} कडे जा (सुमारे {walk} मिनिटे).',
                   f'प्लॅटफॉर्म {assigned} वर पोहोचल्यावर डिस्प्लेवर डब्याची स्थिती तपासा.']}[lang]


# ------------------------ Passenger routes ------------------------

@app.route('/')
def index():
    return render_template('index.html')


def search_trains(q, limit=20):
    """Best matches first: number starts with q, name starts with q, then name contains q."""
    q = q.strip()
    conn = get_db_connection()
    if not q:
        rows = conn.execute('''SELECT train_number, MIN(train_name) AS train_name,
                   MIN(source_station) AS source, MIN(destination_station) AS dest
                   FROM trains GROUP BY train_number ORDER BY train_number LIMIT ?''', (limit,)).fetchall()
    else:
        like_start, like_any = f'{q}%', f'%{q}%'
        rows = conn.execute('''
            SELECT train_number, MIN(train_name) AS train_name,
                   MIN(source_station) AS source, MIN(destination_station) AS dest,
                   MIN(CASE WHEN train_number = ? THEN 0
                            WHEN train_number LIKE ? THEN 1
                            WHEN train_name LIKE ? THEN 2 ELSE 3 END) AS rank
            FROM trains
            WHERE train_number LIKE ? OR train_name LIKE ?
            GROUP BY train_number ORDER BY rank, train_number LIMIT ?''',
            (q, like_start, like_start, like_any, like_any, limit)).fetchall()
    conn.close()
    return [{k: r[k] for k in ('train_number', 'train_name', 'source', 'dest')} for r in rows]


@app.route('/api/search-trains')
def api_search_trains():
    """Typeahead: works with any number of trains because only 20 are ever sent."""
    return jsonify(search_trains(request.args.get('q', ''), 20))


@app.route('/api/trains')
def api_trains():
    return jsonify(search_trains(request.args.get('q', ''), 50))


def resolve_train(train_q):
    """Turn what the user typed (number or name) into ONE train number, or an error."""
    conn = get_db_connection()
    exact = conn.execute('SELECT 1 FROM trains WHERE train_number = ? LIMIT 1', (train_q,)).fetchone()
    if exact:
        conn.close()
        return train_q, None
    rows = conn.execute('''SELECT DISTINCT train_number, train_name FROM trains
                           WHERE train_name LIKE ? ORDER BY (LOWER(train_name) = LOWER(?)) DESC, train_number LIMIT 6''',
                        (f'%{train_q}%', train_q)).fetchall()
    conn.close()
    if not rows:
        return None, (f"No train found for '{train_q}'.", 404)
    exact_name = [r for r in rows if r['train_name'].lower() == train_q.lower()]
    if len(exact_name) == 1 or len(rows) == 1:
        return (exact_name or rows)[0]['train_number'], None
    options = ', '.join(f"{r['train_number']} ({r['train_name']})" for r in rows[:5])
    return None, (f"Several trains match '{train_q}': {options}. Please pick one from the list.", 400)


@app.route('/api/train-stops/<train_number>')
def api_train_stops(train_number):
    """Stops of one train (platform is NOT sent - the check endpoint reveals it)."""
    conn = get_db_connection()
    rows = conn.execute('''SELECT station, departure_time, train_name, source_station, destination_station
                           FROM trains WHERE train_number = ? ORDER BY station''',
                        (train_number.strip(),)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/api/check-platform', methods=['POST'])
def check_platform():
    """
    JSON in : { train, station, current_platform, language, minutes_override? }
    Compares the passenger's platform with the train's arrival platform and scores the risk.
    """
    data = request.get_json(silent=True) or {}
    train_q = str(data.get('train', '')).strip()
    station_q = str(data.get('station', '')).strip()
    language = data.get('language', 'en')
    if language not in ('en', 'hi', 'mr'):
        language = 'en'

    if not train_q or data.get('current_platform') in (None, ''):
        return jsonify({'success': False, 'error': 'Please provide the train number and your current platform.'}), 400
    try:
        current_plat = int(data['current_platform'])
        if current_plat < 1:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({'success': False, 'error': 'Platform must be a positive whole number.'}), 400

    train_no, problem = resolve_train(train_q)
    if problem:
        return jsonify({'success': False, 'error': problem[0]}), problem[1]

    conn = get_db_connection()
    cur = conn.cursor()
    if station_q:
        cur.execute('''SELECT * FROM trains WHERE train_number = ? AND LOWER(station) LIKE LOWER(?)
                       ORDER BY (LOWER(station) = LOWER(?)) DESC LIMIT 1''',
                    (train_no, f'%{station_q}%', station_q))
        record = cur.fetchone()
    else:
        cur.execute('SELECT COUNT(*) AS n FROM trains WHERE train_number = ?', (train_no,))
        if cur.fetchone()['n'] > 1:
            conn.close()
            return jsonify({'success': False,
                            'error': 'This train stops at many stations - please choose your station.'}), 400
        cur.execute('SELECT * FROM trains WHERE train_number = ? LIMIT 1', (train_no,))
        record = cur.fetchone()
    conn.close()

    if not record:
        return jsonify({'success': False,
                        'error': f"Train {train_no} has no record at '{station_q}'. Pick a station from the list."}), 404

    assigned = record['platform']
    is_match = (current_plat == assigned)
    gap = 0 if is_match else abs(current_plat - assigned)
    base_walk = record['walk_minutes']
    crowd = record['crowd_level']
    crowded = 1 if crowd == 'High' else 0

    override = data.get('minutes_override')
    try:
        minutes = int(override) if override not in (None, '') else calculate_minutes_remaining(record['departure_time'])
        minutes = max(1, minutes)
    except (ValueError, TypeError):
        minutes = calculate_minutes_remaining(record['departure_time'])

    # 1) Rule-based baseline
    risk_level, walk, _ = classify_risk(minutes, gap, base_walk, crowded)
    model_used = 'Rule-Based Risk Engine'

    # 2) ML override (same 4 features the model was trained on)
    if ml_model is not None:
        try:
            import pandas as pd
            feats = pd.DataFrame([[minutes, gap, base_walk, crowded]],
                                 columns=['minutes_remaining', 'platform_gap', 'base_walk_minutes', 'crowded'])
            risk_level = str(ml_model.predict(feats)[0])
            conf = int(max(ml_model.predict_proba(feats)[0]) * 100)
            model_used = f'Random Forest Classifier ({conf}% confidence)'
        except Exception as e:
            print(f'[WARN] ML prediction failed: {e}')

    return jsonify({
        'success': True,
        'train_number': record['train_number'],
        'train_name': record['train_name'],
        'source_station': record['source_station'],
        'destination_station': record['destination_station'],
        'station': record['station'],
        'assigned_platform': assigned,
        'current_platform': current_plat,
        'is_match': is_match,
        'platform_gap': gap,
        'alert': build_alert(is_match, current_plat, assigned, language),
        'departure_time': record['departure_time'],
        'minutes_remaining': minutes,
        'estimated_walk_minutes': walk,
        'crowd_level': crowd,
        'risk_level': risk_level,
        'risk_summary': build_summary(is_match, risk_level, assigned, walk, minutes, crowd, language),
        'guidance': generate_guidance_steps(is_match, current_plat, assigned, walk, language),
        'model_used': model_used,
    })


# ------------------------ Admin routes ------------------------

@app.route('/admin')
def admin_dashboard():
    logged_in = session.get('admin_logged_in', False)
    records, metrics, total = [], None, 0
    q = request.args.get('q', '').strip()
    if logged_in:
        conn = get_db_connection()
        total = conn.execute('SELECT COUNT(*) FROM trains').fetchone()[0]
        if q:
            like = f'%{q}%'
            records = conn.execute('''SELECT * FROM trains WHERE train_number LIKE ? OR train_name LIKE ?
                                      OR station LIKE ? ORDER BY train_number, departure_time LIMIT 200''',
                                   (like, like, like)).fetchall()
        else:
            records = conn.execute('SELECT * FROM trains ORDER BY updated_at DESC, id DESC LIMIT 100').fetchall()
        conn.close()
        if os.path.exists(METRICS_FILE):
            try:
                with open(METRICS_FILE, 'r', encoding='utf-8') as f:
                    metrics = json.load(f)
            except Exception as e:
                print(f'[WARN] Could not read metrics: {e}')
    return render_template('admin.html', logged_in=logged_in, records=records, metrics=metrics,
                           ml_active=(ml_model is not None), total=total, q=q,
                           auth_error=request.args.get('auth_error'))


@app.route('/admin/login', methods=['POST'])
def admin_login():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    conn = get_db_connection()
    admin = conn.execute('SELECT * FROM admins WHERE username = ?', (username,)).fetchone()
    conn.close()
    if admin and check_password_hash(admin['password_hash'], password):
        session['admin_logged_in'] = True
        session['admin_user'] = username
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('admin_dashboard', auth_error='Invalid username or password'))


@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/save-train', methods=['POST'])
def admin_save_train():
    """Add a train stop or CHANGE its platform (this is the 'platform change' action)."""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_dashboard'))
    f = request.form
    try:
        row = {
            'train_number': f.get('train_number', '').strip(),
            'train_name': f.get('train_name', '').strip(),
            'source_station': f.get('source_station', '').strip(),
            'destination_station': f.get('destination_station', '').strip(),
            'station': f.get('station', '').strip(),
            'platform': int(f.get('platform', 1)),
            'departure_time': f.get('departure_time', '').strip(),
            'walk_minutes': int(f.get('walk_minutes', 5)),
            'crowd_level': 'High' if f.get('crowd_level') == 'High' else 'Low',
        }
        if not (row['train_number'] and row['train_name'] and row['station'] and row['departure_time']):
            return 'Train number, name, station and departure time are required.', 400
        from prepare_data import norm_time
        row['departure_time'] = norm_time(row['departure_time'])
    except ValueError as e:
        return f'Invalid input: {e}', 400

    conn = get_db_connection()
    upsert_clean_rows(conn.cursor(), [row])
    conn.execute('UPDATE trains SET station_code = ? WHERE train_number = ? AND station = ?',
                 (f.get('station_code', '').strip(), row['train_number'], row['station']))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_dashboard', q=row['train_number']))


@app.route('/admin/delete-train/<int:record_id>', methods=['POST'])
def admin_delete_train(record_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_dashboard'))
    conn = get_db_connection()
    conn.execute('DELETE FROM trains WHERE id = ?', (record_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/import-csv', methods=['POST'])
def admin_import_csv():
    """Accepts the raw project dataset format OR the cleaned train_platforms.csv format."""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_dashboard'))
    up = request.files.get('csv_file')
    if not up or up.filename == '':
        return redirect(url_for('admin_dashboard'))
    try:
        text = up.stream.read().decode('utf-8-sig')
        reader = csv.DictReader(text.splitlines())
        cols = set(reader.fieldnames or [])
        rows = list(reader)
        raw_cols = {'train_number', 'train_name', 'station_name', 'departure_time',
                    'train_arrival_platform', 'platform_crowded'}
        clean_cols = {'train_number', 'train_name', 'station', 'platform', 'departure_time'}
        if raw_cols.issubset(cols):
            cleaned = clean_rows(rows)
        elif clean_cols.issubset(cols):
            from prepare_data import norm_time, platform_number, crowd_label
            cleaned = [{
                'train_number': r['train_number'].strip(), 'train_name': r['train_name'].strip(),
                'source_station': r.get('source_station', '').strip(),
                'destination_station': r.get('destination_station', '').strip(),
                'station': r['station'].strip(), 'platform': platform_number(r['platform']),
                'departure_time': norm_time(r['departure_time']),
                'walk_minutes': int(r.get('walk_minutes') or 5),
                'crowd_level': crowd_label(r.get('crowd_level', 'Low')),
            } for r in rows]
        else:
            return ('CSV headers not recognised. Use the project dataset columns '
                    '(train_number, train_name, station_name, departure_time, train_arrival_platform, '
                    'platform_crowded) or train_number, train_name, station, platform, departure_time.'), 400
        conn = get_db_connection()
        upsert_clean_rows(conn.cursor(), cleaned)
        conn.commit()
        conn.close()
    except Exception as e:
        return f'Error parsing CSV: {e}', 500
    return redirect(url_for('admin_dashboard'))


init_db()
load_ml_model()


if __name__ == '__main__':
    print('=' * 60)
    print('  RAILGUARD AI SERVER READY')
    print('  Passenger app : http://127.0.0.1:5000')
    print('  Admin portal  : http://127.0.0.1:5000/admin')
    print('=' * 60)

    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=False
    )


