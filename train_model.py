"""
RailGuard AI - Train the Random Forest risk model.

Run:  python train_model.py
Reads  data/risk_training_dataset.csv
Writes models/risk_model.joblib  and  models/model_metrics.json
"""
import json
import os

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import cross_val_score, train_test_split

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
TRAIN_CSV = os.path.join(BASE_DIR, 'data', 'risk_training_dataset.csv')
MODELS_DIR = os.path.join(BASE_DIR, 'models')
MODEL_FILE = os.path.join(MODELS_DIR, 'risk_model.joblib')
METRICS_FILE = os.path.join(MODELS_DIR, 'model_metrics.json')

# Raw inputs only. estimated_walk / time_buffer are deliberately NOT features:
# they are computed from the label rule, so using them would be data leakage.
FEATURES = ['minutes_remaining', 'platform_gap', 'base_walk_minutes', 'crowded']
CLASSES = ['High', 'Medium', 'Low']


def main():
    os.makedirs(MODELS_DIR, exist_ok=True)
    df = pd.read_csv(TRAIN_CSV)
    X, y = df[FEATURES], df['risk_label']

    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

    model = RandomForestClassifier(n_estimators=200, max_depth=12, class_weight='balanced',
                                   random_state=42, n_jobs=-1)
    model.fit(X_tr, y_tr)
    pred = model.predict(X_te)

    acc = accuracy_score(y_te, pred)
    cv = cross_val_score(model, X, y, cv=5)
    majority = y_te.value_counts(normalize=True).max()
    report = classification_report(y_te, pred, labels=CLASSES, output_dict=True, zero_division=0)
    cm = confusion_matrix(y_te, pred, labels=CLASSES).tolist()

    metrics = {
        'dataset_rows': int(len(df)),
        'train_rows': int(len(X_tr)),
        'test_rows': int(len(X_te)),
        'accuracy': round(acc * 100, 2),
        'cv_accuracy_mean': round(cv.mean() * 100, 2),
        'cv_accuracy_std': round(cv.std() * 100, 2),
        'majority_baseline': round(majority * 100, 2),
        'class_distribution': {k: int(v) for k, v in y.value_counts().items()},
        'per_class': {c: {'precision': round(report[c]['precision'] * 100, 1),
                          'recall': round(report[c]['recall'] * 100, 1),
                          'f1': round(report[c]['f1-score'] * 100, 1),
                          'support': int(report[c]['support'])} for c in CLASSES},
        'confusion_matrix': {'labels': CLASSES, 'matrix': cm},
        'feature_importance': {f: round(float(i) * 100, 1)
                               for f, i in sorted(zip(FEATURES, model.feature_importances_),
                                                  key=lambda t: -t[1])},
        'features': FEATURES,
    }

    joblib.dump(model, MODEL_FILE)
    with open(METRICS_FILE, 'w', encoding='utf-8') as f:
        json.dump(metrics, f, indent=2)

    print(f'[OK] Test accuracy: {metrics["accuracy"]}%  (5-fold CV: {metrics["cv_accuracy_mean"]} +/- {metrics["cv_accuracy_std"]})')
    print(f'     Majority-class baseline: {metrics["majority_baseline"]}%')
    print(classification_report(y_te, pred, labels=CLASSES, zero_division=0))
    print(f'[OK] Saved {MODEL_FILE}')


if __name__ == '__main__':
    main()
