import random
import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from pathlib import Path
from sqlalchemy import select, insert
from .database import now
from .models import Customer, CustomerEvent, Product, Channel, Campaign, Order, SupportInteraction, GraphEntity, GraphRelationship
from .schemas import EventInput, utc
from .temporal_graph import ingest_edge, event_graph_records

CHANNELS = ['website', 'mobile', 'email', 'ads', 'support', 'social']


def ensure_channels(db):
    for name in CHANNELS:
        if not db.get(Channel, name):
            db.add(Channel(id=name, name=name.title()))
    db.flush()


def add_event(db, payload: EventInput, source='import'):
    if not db.get(Customer, payload.customer_id):
        raise ValueError(f'Unknown customer {payload.customer_id}; import customers first')
    if db.get(CustomerEvent, payload.event_id):
        return None
    ensure_channels(db)
    event = CustomerEvent(id=payload.event_id, **payload.model_dump(exclude={'event_id'}), recorded_at=utc(now()), source=source)
    db.add(event)
    db.flush()
    if payload.event_type == 'purchase':
        db.add(Order(id=f'order-{event.id}', event_id=event.id, customer_id=event.customer_id, product_id=event.entity_id, amount=float(event.properties.get('amount', 0)), ordered_at=event.event_time))
    if payload.event_type == 'support':
        db.add(SupportInteraction(id=f'ticket-{event.id}', event_id=event.id, customer_id=event.customer_id))
    ingest_edge(db, event)
    return event


def seed_demo(db, export_dir=None):
    if db.scalar(select(Customer.id).limit(1)):
        return {'seeded': False, 'reason': 'Database already contains customers'}
    rng = random.Random(42)
    ensure_channels(db)
    products = [('P001', 'Studio headphones', 'Audio', 149), ('P002', 'Trail backpack', 'Travel', 89), ('P003', 'Smart fitness watch', 'Wearables', 229), ('P004', 'Everyday sneakers', 'Apparel', 119), ('P005', 'Desk lamp', 'Home', 59), ('P006', 'Wireless keyboard', 'Electronics', 99)]
    for id_, name, category, price in products:
        db.add(Product(id=id_, name=name, category=category, price=price))
    db.add(Campaign(id='CMP01', name='Autumn discovery — synthetic campaign', channel='email'))
    anchor = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    start = anchor - timedelta(days=180)
    customers, events = [], []
    for i in range(1, 121):
        customer = {'id': f'C{i:03}', 'name': f'Demo Customer {i:03}', 'email': f'customer{i:03}@example.test', 'region': rng.choice(['North', 'South', 'East', 'West'])}
        customers.append(customer)
        db.add(Customer(**customer, source='synthetic-demo', created_at=utc(start.isoformat())))
    db.flush()
    sequence = 0
    for customer in customers:
        active_bias = rng.random()
        for day in range(180):
            if rng.random() > (0.10 if active_bias > .3 else (.08 if day < 90 else .008)):
                continue
            when = start + timedelta(days=day, hours=rng.randrange(8, 22), minutes=rng.randrange(50))
            product = rng.choice(products)
            channel = rng.choice(['website', 'mobile', 'email', 'ads', 'social'])
            path = ['website_visit', 'product_view']
            if rng.random() < .22:
                path.insert(0, 'email_open')
            if rng.random() < .65:
                path.append('add_to_cart')
                if rng.random() < (.65 if active_bias > .3 else .2):
                    path.append('purchase')
                    if rng.random() < .12:
                        path.append('return')
                    elif rng.random() < .12:
                        path.append('review')
            if rng.random() < .08:
                path.append('support')
            for position, type_ in enumerate(path):
                sequence += 1
                payload = {'event_id': f'EVT{sequence:06}', 'customer_id': customer['id'], 'event_type': type_, 'entity_id': 'CMP01' if type_ == 'email_open' else product[0], 'channel': 'support' if type_ == 'support' else ('email' if type_ == 'email_open' else channel), 'event_time': utc((when + timedelta(minutes=position * 4)).isoformat()), 'properties': {'amount': product[3]} if type_ in ('purchase', 'return') else {'category': product[2]}}
                events.append(payload)
    # Avoid per-event network round trips when cold-starting against managed
    # PostgreSQL. API/file ingestion still uses the validated add_event path.
    event_rows, relationship_rows, order_rows, support_rows = [], [], [], []
    entities = {}
    for payload in events:
        parsed = EventInput(**payload)
        row = dict(id=parsed.event_id, **parsed.model_dump(exclude={'event_id'}), recorded_at=utc(now()), source='synthetic-demo')
        event_rows.append(row)
        nodes, edges = event_graph_records(CustomerEvent(**row))
        entities.update({n['id']: n for n in nodes})
        relationship_rows.extend(edges)
        if parsed.event_type == 'purchase':
            order_rows.append(dict(id='order-' + row['id'], event_id=row['id'], customer_id=row['customer_id'], product_id=row['entity_id'], amount=float(row['properties'].get('amount', 0)), ordered_at=row['event_time']))
        elif parsed.event_type == 'support':
            support_rows.append(dict(id='ticket-' + row['id'], event_id=row['id'], customer_id=row['customer_id'], status='open'))
    db.execute(insert(CustomerEvent), event_rows)
    db.execute(insert(GraphEntity), list(entities.values()))
    db.execute(insert(GraphRelationship), relationship_rows)
    if order_rows:
        db.execute(insert(Order), order_rows)
    if support_rows:
        db.execute(insert(SupportInteraction), support_rows)
    db.commit()
    if export_dir:
        import csv
        folder = Path(export_dir)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / 'customers.json').write_text(json.dumps(customers, indent=2), encoding='utf-8')
        (folder / 'events.json').write_text(json.dumps(events, indent=2), encoding='utf-8')
        for name, rows in [('customers', customers), ('events', events), ('products', [dict(zip(['id', 'name', 'category', 'price'], p)) for p in products]), ('channels', [{'id': x, 'name': x.title()} for x in CHANNELS]), ('campaigns', [{'id': 'CMP01', 'name': 'Autumn discovery', 'channel': 'email'}]), ('orders', [{'id': 'order-' + e['event_id'], 'event_id': e['event_id'], 'customer_id': e['customer_id'], 'product_id': e['entity_id'], 'amount': e['properties']['amount'], 'ordered_at': e['event_time']} for e in events if e['event_type'] == 'purchase']), ('support_interactions', [{'id': 'ticket-' + e['event_id'], 'event_id': e['event_id'], 'customer_id': e['customer_id'], 'status': 'open'} for e in events if e['event_type'] == 'support'])]:
            with (folder / f'{name}.csv').open('w', newline='', encoding='utf-8') as stream:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows([{k: json.dumps(v) if isinstance(v, dict) else v for k, v in row.items()} for row in rows])
    return {'seeded': True, 'customers': len(customers), 'events': len(events), 'source': 'synthetic-demo'}
