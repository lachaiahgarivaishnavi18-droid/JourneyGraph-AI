from collections import Counter
from typing import Protocol
import os
import networkx as nx
from sqlalchemy import select
from .models import CustomerEvent, GraphEntity, GraphRelationship, Customer
from .schemas import utc

RELATIONS = {'product_view': 'CUSTOMER_VIEWED_PRODUCT', 'add_to_cart': 'CUSTOMER_ADDED_TO_CART', 'purchase': 'CUSTOMER_PURCHASED', 'email_open': 'CUSTOMER_OPENED_CAMPAIGN_EMAIL', 'support': 'CUSTOMER_CONTACTED_SUPPORT', 'return': 'CUSTOMER_RETURNED_PRODUCT'}


class GraphStore(Protocol):
    def snapshot(self, at=None, known_at=None, customer_id=None): ...


def ingest_edge(db, event):
    source = f'customer:{event.customer_id}'
    kind = 'product' if event.event_type in ('product_view', 'add_to_cart', 'purchase', 'return') else ('campaign' if event.event_type == 'email_open' else 'touchpoint')
    target = f'{kind}:{event.entity_id}'
    for id_, type_, label in [(source, 'customer', event.customer_id), (target, kind, event.entity_id), (f'channel:{event.channel}', 'channel', event.channel)]:
        if not db.get(GraphEntity, id_):
            db.add(GraphEntity(id=id_, kind=type_, label=label))
    db.flush()
    for suffix, destination, relation in [('entity', target, RELATIONS.get(event.event_type, 'CUSTOMER_' + event.event_type.upper())), ('channel', f'channel:{event.channel}', 'CUSTOMER_USED_CHANNEL')]:
        id_ = f'{event.id}:{suffix}'
        if not db.get(GraphRelationship, id_):
            db.add(GraphRelationship(id=id_, source=source, target=destination, relation=relation, event_id=event.id, valid_from=event.event_time, valid_to=event.valid_to, recorded_at=event.recorded_at, provenance={'source': event.source, 'event_type': event.event_type, 'channel': event.channel}))
    db.flush()


class LocalGraphStore:
    def __init__(self, db):
        self.db = db

    def build(self):
        for event in self.db.scalars(select(CustomerEvent)):
            ingest_edge(self.db, event)
        self.db.flush()
        return {'entities': len(list(self.db.scalars(select(GraphEntity)))), 'relationships': len(list(self.db.scalars(select(GraphRelationship)))), 'storage': 'SQL temporal tables + NetworkX query projection'}

    def snapshot(self, at=None, known_at=None, customer_id=None):
        statement = select(GraphRelationship)
        if at:
            at = utc(at)
            statement = statement.where(GraphRelationship.valid_from <= at, (GraphRelationship.valid_to.is_(None) | (GraphRelationship.valid_to > at)))
        if known_at:
            statement = statement.where(GraphRelationship.recorded_at <= utc(known_at))
        if customer_id:
            statement = statement.where(GraphRelationship.source == f'customer:{customer_id}')
        edges = list(self.db.scalars(statement.order_by(GraphRelationship.valid_from, GraphRelationship.id)))
        ids = {x for e in edges for x in (e.source, e.target)}
        graph = nx.MultiDiGraph()
        nodes = [{'id': n.id, 'kind': n.kind, 'label': n.label} for n in self.db.scalars(select(GraphEntity).where(GraphEntity.id.in_(ids)))] if ids else []
        graph.add_nodes_from(ids)
        output = []
        for edge in edges:
            graph.add_edge(edge.source, edge.target, key=edge.id)
            output.append({k: getattr(edge, k) for k in ('id', 'source', 'target', 'relation', 'event_id', 'valid_from', 'valid_to', 'recorded_at', 'provenance')})
        return {'nodes': nodes, 'edges': output, 'at': at, 'known_at': known_at, 'semantics': 'Cumulative historical facts: valid_from <= at < valid_to; open-ended event facts persist.', 'components': nx.number_weakly_connected_components(graph) if nodes else 0}

    def compare(self, before, after, known_at=None):
        first = {e['id']: e for e in self.snapshot(before, known_at)['edges']}
        second = {e['id']: e for e in self.snapshot(after, known_at)['edges']}
        return {'added': [second[k] for k in second.keys() - first.keys()], 'removed': [first[k] for k in first.keys() - second.keys()], 'unchanged': len(first.keys() & second.keys())}

    def patterns(self):
        journeys = {}
        for e in self.db.scalars(select(CustomerEvent).order_by(CustomerEvent.event_time, CustomerEvent.id)):
            journeys.setdefault(e.customer_id, []).append(e.event_type)
        pairs = Counter()
        for events in journeys.values():
            pairs.update(set(zip(events, events[1:])))
        return [{'path': list(path), 'customers': count} for path, count in pairs.most_common(20)]


class Neo4jGraphStore:
    """Explicit SQL-to-Neo4j projection. SQL remains the ingestion source of truth."""
    def __init__(self, db):
        from neo4j import GraphDatabase
        self.local = LocalGraphStore(db)
        self.driver = GraphDatabase.driver(os.environ['NEO4J_URI'], auth=(os.environ['NEO4J_USER'], os.environ['NEO4J_PASSWORD']))

    def sync(self):
        data = self.local.snapshot()
        try:
            with self.driver.session() as session:
                session.run('CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (n:Entity) REQUIRE n.id IS UNIQUE').consume()
                session.run('UNWIND $nodes AS x MERGE (n:Entity {id:x.id}) SET n.kind=x.kind, n.label=x.label', nodes=data['nodes']).consume()
                session.run('UNWIND $edges AS x MATCH (a:Entity {id:x.source}), (b:Entity {id:x.target}) MERGE (a)-[r:FACT {id:x.id}]->(b) SET r.relation=x.relation, r.valid_from=x.valid_from, r.valid_to=x.valid_to, r.recorded_at=x.recorded_at, r.event_id=x.event_id', edges=data['edges']).consume()
            return {'synced_edges': len(data['edges'])}
        finally:
            self.driver.close()

    def snapshot(self, at=None, known_at=None, customer_id=None):
        try:
            with self.driver.session() as session:
                result = session.run('MATCH (a:Entity)-[r:FACT]->(b:Entity) WHERE ($at IS NULL OR (r.valid_from <= $at AND (r.valid_to IS NULL OR r.valid_to > $at))) AND ($known IS NULL OR r.recorded_at <= $known) AND ($customer IS NULL OR a.id = $customer) RETURN properties(a) AS a, properties(b) AS b, properties(r) AS r', at=utc(at) if at else None, known=utc(known_at) if known_at else None, customer=f'customer:{customer_id}' if customer_id else None)
                nodes, edges = {}, []
                for row in result:
                    nodes[row['a']['id']] = row['a']
                    nodes[row['b']['id']] = row['b']
                    edges.append({**row['r'], 'source': row['a']['id'], 'target': row['b']['id']})
                return {'nodes': list(nodes.values()), 'edges': edges, 'storage': 'neo4j'}
        finally:
            self.driver.close()
