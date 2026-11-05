from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from statistics import mean
from sqlalchemy import select
from .models import Customer, CustomerEvent, Segment
from .schemas import utc

STAGES = [('Awareness', {'website_visit', 'ad_click', 'email_open', 'app_open'}), ('Acquisition', {'search', 'product_view'}), ('Consideration', {'add_to_cart'}), ('Conversion', {'purchase'}), ('Retention', {'purchase'}), ('Advocacy', {'review'})]


def events_query(db, start=None, end=None, channel=None, product=None, event_type=None, segment=None, stage=None, customer_id=None):
    query = select(CustomerEvent)
    if start:
        query = query.where(CustomerEvent.event_time >= utc(start))
    if end:
        query = query.where(CustomerEvent.event_time <= utc(end))
    if channel:
        query = query.where(CustomerEvent.channel == channel)
    if product:
        query = query.where(CustomerEvent.entity_id == product)
    if event_type:
        query = query.where(CustomerEvent.event_type == event_type)
    if segment:
        query = query.where(CustomerEvent.customer_id.in_(select(Segment.customer_id).where(Segment.label == segment)))
    if stage:
        types = dict(STAGES).get(stage, set())
        query = query.where(CustomerEvent.event_type.in_(types))
    if customer_id:
        query = query.where(CustomerEvent.customer_id == customer_id)
    return list(db.scalars(query.order_by(CustomerEvent.event_time, CustomerEvent.id)))


def as_date(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def features(events, reference):
    purchases = [e for e in events if e.event_type == 'purchase']
    recency = max(0, (reference - as_date(events[-1].event_time)).days) if events else 999
    frequency = len(purchases)
    monetary = sum(float(e.properties.get('amount', 0)) for e in purchases)
    label = 'Inactive' if recency > 30 else ('Champions' if frequency >= 5 else ('Returning' if frequency >= 2 else ('New buyers' if frequency else 'Explorers')))
    return {'recency_days': recency, 'frequency': frequency, 'monetary': round(monetary, 2), 'touchpoints': len(events), 'channels': len({e.channel for e in events}), 'segment': label}


def segment_customers(db):
    all_events = events_query(db)
    reference = max([as_date(e.event_time) for e in all_events], default=datetime.now(timezone.utc))
    by_customer = defaultdict(list)
    for e in all_events:
        by_customer[e.customer_id].append(e)
    output = []
    for customer in db.scalars(select(Customer).order_by(Customer.id)):
        f = features(by_customer[customer.id], reference)
        db.merge(Segment(customer_id=customer.id, label=f['segment'], features=f))
        output.append({'customer_id': customer.id, **f})
    db.flush()
    return output


def profile(db, id_, events=None):
    customer = db.get(Customer, id_)
    if not customer:
        return None
    events = events if events is not None else events_query(db, customer_id=id_)
    all_latest = db.scalar(select(CustomerEvent.event_time).order_by(CustomerEvent.event_time.desc()).limit(1))
    reference = as_date(all_latest) if all_latest else datetime.now(timezone.utc)
    f = features(events, reference)
    preferences = Counter(e.entity_id for e in events if e.event_type in ('product_view', 'purchase'))
    return {'id': customer.id, 'name': customer.name, 'region': customer.region, 'source': customer.source, 'created_at': customer.created_at, **f, 'preferred_products': [{'product_id': p, 'interactions': n} for p, n in preferences.most_common(3)], 'last_seen': events[-1].event_time if events else None}


def event_dict(e):
    return {k: getattr(e, k) for k in ('id', 'customer_id', 'event_type', 'entity_id', 'channel', 'event_time', 'recorded_at', 'valid_to', 'properties', 'source')}


def journey(db, id_, **filters):
    events = events_query(db, customer_id=id_, **filters)
    purchase_count = 0
    timeline = []
    for i, e in enumerate(events):
        if e.event_type == 'purchase':
            purchase_count += 1
        stage = next((s for s, types in STAGES if e.event_type in types), 'Retention')
        if e.event_type == 'purchase' and purchase_count > 1:
            stage = 'Retention'
        timeline.append({**event_dict(e), 'sequence': i + 1, 'stage': stage})
    return {'customer_id': id_, 'events': timeline, 'channel_transitions': sum(a.channel != b.channel for a, b in zip(events, events[1:])), 'duration_days': round((as_date(events[-1].event_time) - as_date(events[0].event_time)).total_seconds() / 86400, 2) if events else 0}


def analytics(db, **filters):
    events = events_query(db, **filters)
    grouped = defaultdict(list)
    for e in events:
        grouped[e.customer_id].append(e)
    all_customers = list(db.scalars(select(Customer)))
    filtered = any(v for v in filters.values())
    denominator = len(grouped) if filtered else len(all_customers)
    purchase_customers = {e.customer_id for e in events if e.event_type == 'purchase'}
    cart_customers = {e.customer_id for e in events if e.event_type == 'add_to_cart'}
    latest = max([as_date(e.event_time) for e in events], default=datetime.now(timezone.utc))
    active = {e.customer_id for e in events if as_date(e.event_time) >= latest - timedelta(days=30)}
    counts = Counter(e.customer_id for e in events if e.event_type == 'purchase')
    revenue = sum(float(e.properties.get('amount', 0)) * (-1 if e.event_type == 'return' else 1) for e in events if e.event_type in ('purchase', 'return'))
    durations = [(as_date(es[-1].event_time) - as_date(es[0].event_time)).total_seconds() / 86400 for es in grouped.values()]
    # Sequential funnel: a customer advances only after the previous stage.
    stages = [('Visit', {'website_visit', 'ad_click', 'email_open', 'app_open'}), ('View', {'product_view', 'search'}), ('Cart', {'add_to_cart'}), ('Purchase', {'purchase'})]
    funnel_counts = [0] * len(stages)
    for es in grouped.values():
        position = 0
        for e in es:
            if position < len(stages) and e.event_type in stages[position][1]:
                funnel_counts[position] += 1
                position += 1
    funnel = [{'stage': name, 'customers': count, 'dropoff': round((1 - count / funnel_counts[i-1]) * 100, 2) if i and funnel_counts[i-1] else 0} for i, ((name, _), count) in enumerate(zip(stages, funnel_counts))]
    channel_stats = []
    for channel in sorted({e.channel for e in events}):
        es = [e for e in events if e.channel == channel]
        users = {e.customer_id for e in es}
        buyers = {e.customer_id for e in es if e.event_type == 'purchase'}
        channel_stats.append({'channel': channel, 'interactions': len(es), 'customers': len(users), 'conversions': len(buyers), 'conversion_rate': round(len(buyers) / len(users) * 100, 2) if users else 0})
    daily = defaultdict(lambda: {'interactions': 0, 'purchases': 0, 'revenue': 0})
    heatmap = Counter()
    for e in events:
        daily[e.event_time[:10]]['interactions'] += 1
        dt = as_date(e.event_time)
        heatmap[(dt.weekday(), dt.hour)] += 1
        if e.event_type == 'purchase':
            daily[e.event_time[:10]]['purchases'] += 1
            daily[e.event_time[:10]]['revenue'] += float(e.properties.get('amount', 0))
    segments = Counter(features(es, latest)['segment'] for es in grouped.values())
    segment_conversion = []
    for label, total in segments.items():
        buyers = sum(id_ in purchase_customers for id_, es in grouped.items() if features(es, latest)['segment'] == label)
        segment_conversion.append({'segment': label, 'customers': total, 'purchasing_customers': buyers, 'conversion_rate': round(buyers / total * 100, 2)})
    paths = Counter(' → '.join(e.event_type for e in es[:6]) for es in grouped.values())
    cohorts = defaultdict(lambda: {'customers': 0, 'converted': 0, 'repeat': 0})
    for id_, es in grouped.items():
        month = es[0].event_time[:7]
        cohorts[month]['customers'] += 1
        cohorts[month]['converted'] += int(id_ in purchase_customers)
        cohorts[month]['repeat'] += int(counts[id_] > 1)
    return {'metrics': {'total_customers': denominator, 'active_customers': len(active), 'conversion_rate': round(len(purchase_customers) / denominator * 100, 2) if denominator else 0, 'dropoff_rate': round(len(cart_customers - purchase_customers) / len(cart_customers) * 100, 2) if cart_customers else 0, 'total_interactions': len(events), 'average_journey_days': round(mean(durations), 2) if durations else 0, 'average_touchpoints': round(len(events) / denominator, 2) if denominator else 0, 'repeat_purchase_rate': round(sum(v > 1 for v in counts.values()) / len(purchase_customers) * 100, 2) if purchase_customers else 0, 'retention_rate': round(len(active) / denominator * 100, 2) if denominator else 0, 'inactivity_rate': round((denominator - len(active)) / denominator * 100, 2) if denominator else 0, 'net_revenue': round(revenue, 2), 'observed_value_per_customer': round(revenue / denominator, 2) if denominator else 0}, 'definitions': {'population': 'Customers with matching events' if filtered else 'All registered customers', 'conversion_rate': 'Distinct purchasing customers / population', 'active_customers': 'Customers with an event within 30 days of latest matching event', 'dropoff_rate': 'Cart customers with no purchase in selected period / cart customers; descriptive, not causal', 'retention_rate': '30-day active share; activity proxy, not longitudinal retention', 'observed_value_per_customer': 'Net recorded purchase/return value / population; not predicted lifetime value', 'reference_time': utc(latest.isoformat()), 'funnel': 'Ordered first visit → view → cart → purchase per customer in filtered events'}, 'funnel': funnel, 'channels': channel_stats, 'trend': [{'date': d, **v} for d, v in sorted(daily.items())], 'segments': [{'name': n, 'customers': c} for n, c in segments.items()], 'segment_conversion': segment_conversion, 'paths': [{'path': p, 'customers': c} for p, c in paths.most_common(10)], 'cohorts': [{'month': m, **v} for m, v in sorted(cohorts.items())], 'heatmap': [{'day': d, 'hour': h, 'events': n} for (d, h), n in sorted(heatmap.items())], 'sources': dict(Counter(e.source for e in events))}
