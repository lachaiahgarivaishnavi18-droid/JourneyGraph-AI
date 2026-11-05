from collections import defaultdict
from datetime import timedelta
from uuid import uuid4
import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, balanced_accuracy_score, brier_score_loss
from .analytics import events_query, as_date
from .models import Prediction

FEATURES = ['recency_days', 'events_30d', 'purchases_30d', 'cart_events_30d', 'support_events_30d', 'channels_30d']


def vector(events, cutoff):
    past = [e for e in events if as_date(e.event_time) <= cutoff]
    recent = [e for e in past if as_date(e.event_time) > cutoff - timedelta(days=30)]
    return [min(180, (cutoff - as_date(past[-1].event_time)).total_seconds() / 86400) if past else 180, len(recent), sum(e.event_type == 'purchase' for e in recent), sum(e.event_type == 'add_to_cart' for e in recent), sum(e.event_type == 'support' for e in recent), len({e.channel for e in recent})]


def predict(db, kind='churn', customer_id=None, persist=True):
    events = events_query(db)
    grouped = defaultdict(list)
    for e in events:
        grouped[e.customer_id].append(e)
    if not events or (as_date(events[-1].event_time) - as_date(events[0].event_time)).days < 100 or len(grouped) < 40:
        return {'status': 'insufficient_data', 'scores': [], 'limitations': ['Need at least 40 customers and 100 days of events with observed future outcomes.']}
    latest = as_date(events[-1].event_time)
    train_cutoff, test_cutoff = latest - timedelta(days=60), latest - timedelta(days=30)
    def dataset(cutoff):
        rows, labels, ids = [], [], []
        for id_, es in sorted(grouped.items()):
            if not any(as_date(e.event_time) <= cutoff for e in es):
                continue
            future = [e for e in es if cutoff < as_date(e.event_time) <= cutoff + timedelta(days=30)]
            label = int(not future) if kind == 'churn' else int(any(e.event_type == 'purchase' for e in future))
            rows.append(vector(es, cutoff))
            labels.append(label)
            ids.append(id_)
        return np.array(rows), np.array(labels), ids
    x_train, y_train, train_ids = dataset(train_cutoff)
    x_test, y_test, test_ids = dataset(test_cutoff)
    if len(y_test) < 20 or len(set(y_train)) < 2 or len(set(y_test)) < 2 or min(np.bincount(y_train)) < 5:
        return {'status': 'insufficient_data', 'scores': [], 'limitations': ['Training and temporal holdout need both outcome classes; at least five examples per training class.']}
    model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, class_weight='balanced', random_state=42))
    model.fit(x_train, y_train)
    test_scores = model.predict_proba(x_test)[:, 1]
    metrics = {'roc_auc': round(float(roc_auc_score(y_test, test_scores)), 4), 'balanced_accuracy': round(float(balanced_accuracy_score(y_test, test_scores >= .5)), 4), 'brier_score': round(float(brier_score_loss(y_test, test_scores)), 4), 'baseline_accuracy': round(float(max(np.mean(y_test), 1-np.mean(y_test))), 4), 'train_customers': len(y_train), 'test_customers': len(y_test), 'test_positive_rate': round(float(np.mean(y_test)), 4), 'train_features_until': train_cutoff.isoformat(), 'train_labels_until': test_cutoff.isoformat(), 'holdout_features_until': test_cutoff.isoformat(), 'holdout_labels_until': latest.isoformat()}
    coefficients = model[-1].coef_[0]
    scores = []
    for id_, es in sorted(grouped.items()):
        if customer_id and id_ != customer_id:
            continue
        values = vector(es, latest)
        probability = float(model.predict_proba([values])[0, 1])
        impacts = coefficients * model[0].transform([values])[0]
        result = {'customer_id': id_, 'score': round(probability, 4), 'risk': 'High' if probability >= .7 else ('Medium' if probability >= .4 else 'Low'), 'features': dict(zip(FEATURES, values)), 'explanations': [{'feature': FEATURES[i], 'log_odds_contribution': round(float(impacts[i]), 3)} for i in np.argsort(abs(impacts))[-3:][::-1]], 'confidence': 'Uncalibrated score; uncertainty intervals unavailable'}
        scores.append(result)
        if persist:
            db.add(Prediction(id=str(uuid4()), customer_id=id_, kind=kind, result=result))
    return {'status': 'evaluated', 'kind': kind, 'model': 'StandardScaler + balanced logistic regression', 'target': 'No events in next 30 days (inactivity proxy)' if kind == 'churn' else 'Purchase within next 30 days', 'metrics': metrics, 'scores': scores, 'limitations': ['Single forward temporal holdout; customers may appear in both windows.', 'Synthetic-data performance is demonstration only, not production validation.', 'Scores are not calibrated probabilities or causal estimates.', 'No-event labels require complete tracking; observation gaps can resemble churn.']}
