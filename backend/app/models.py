from sqlalchemy import String, ForeignKey, Float, Integer, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base, now


class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(512))
    role: Mapped[str] = mapped_column(String(20), default='viewer')
    created_at: Mapped[str] = mapped_column(String(40), default=now)


class Customer(Base):
    __tablename__ = 'customers'
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(254), default='')
    region: Mapped[str] = mapped_column(String(80), default='Unknown')
    source: Mapped[str] = mapped_column(String(80), default='import')
    created_at: Mapped[str] = mapped_column(String(40), default=now)
    updated_at: Mapped[str] = mapped_column(String(40), default=now)


class Product(Base):
    __tablename__ = 'products'
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    category: Mapped[str] = mapped_column(String(80))
    price: Mapped[float] = mapped_column(Float)


class Channel(Base):
    __tablename__ = 'channels'
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(80))


class Campaign(Base):
    __tablename__ = 'campaigns'
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    channel: Mapped[str] = mapped_column(ForeignKey('channels.id'))


class CustomerEvent(Base):
    __tablename__ = 'customer_events'
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey('customers.id'), index=True)
    event_type: Mapped[str] = mapped_column(String(50), index=True)
    entity_id: Mapped[str] = mapped_column(String(80))
    channel: Mapped[str] = mapped_column(ForeignKey('channels.id'), index=True)
    event_time: Mapped[str] = mapped_column(String(40), index=True)
    recorded_at: Mapped[str] = mapped_column(String(40), default=now, index=True)
    valid_to: Mapped[str | None] = mapped_column(String(40), nullable=True)
    properties: Mapped[dict] = mapped_column(JSON, default=dict)
    source: Mapped[str] = mapped_column(String(80), default='import')


class Order(Base):
    __tablename__ = 'orders'
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    event_id: Mapped[str] = mapped_column(ForeignKey('customer_events.id'), unique=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey('customers.id'), index=True)
    product_id: Mapped[str] = mapped_column(String(80))
    amount: Mapped[float] = mapped_column(Float)
    ordered_at: Mapped[str] = mapped_column(String(40))


class SupportInteraction(Base):
    __tablename__ = 'support_interactions'
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    event_id: Mapped[str] = mapped_column(ForeignKey('customer_events.id'), unique=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey('customers.id'))
    status: Mapped[str] = mapped_column(String(40), default='open')


class GraphEntity(Base):
    __tablename__ = 'graph_entities'
    id: Mapped[str] = mapped_column(String(180), primary_key=True)
    kind: Mapped[str] = mapped_column(String(40))
    label: Mapped[str] = mapped_column(String(160))


class GraphRelationship(Base):
    __tablename__ = 'graph_relationships'
    id: Mapped[str] = mapped_column(String(180), primary_key=True)
    source: Mapped[str] = mapped_column(ForeignKey('graph_entities.id'), index=True)
    target: Mapped[str] = mapped_column(ForeignKey('graph_entities.id'), index=True)
    relation: Mapped[str] = mapped_column(String(60))
    event_id: Mapped[str] = mapped_column(ForeignKey('customer_events.id'), index=True)
    valid_from: Mapped[str] = mapped_column(String(40), index=True)
    valid_to: Mapped[str | None] = mapped_column(String(40), nullable=True)
    recorded_at: Mapped[str] = mapped_column(String(40), index=True)
    provenance: Mapped[dict] = mapped_column(JSON)


class Execution(Base):
    __tablename__ = 'agent_executions'
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    customer_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(String(30))
    started_at: Mapped[str] = mapped_column(String(40), default=now)
    finished_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    outputs: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(String(500), nullable=True)


class AgentOutput(Base):
    __tablename__ = 'agent_outputs'
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    execution_id: Mapped[str] = mapped_column(ForeignKey('agent_executions.id'), index=True)
    agent: Mapped[str] = mapped_column(String(80))
    output: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[str] = mapped_column(String(40), default=now)


class Segment(Base):
    __tablename__ = 'customer_segments'
    customer_id: Mapped[str] = mapped_column(ForeignKey('customers.id'), primary_key=True)
    label: Mapped[str] = mapped_column(String(60), index=True)
    features: Mapped[dict] = mapped_column(JSON)
    updated_at: Mapped[str] = mapped_column(String(40), default=now)


class Prediction(Base):
    __tablename__ = 'predictions'
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey('customers.id'), index=True)
    kind: Mapped[str] = mapped_column(String(40))
    result: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[str] = mapped_column(String(40), default=now)


class Recommendation(Base):
    __tablename__ = 'recommendations'
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey('customers.id'), index=True)
    result: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[str] = mapped_column(String(40), default=now)


class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    actor: Mapped[str] = mapped_column(String(80))
    action: Mapped[str] = mapped_column(String(80))
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[str] = mapped_column(String(40), default=now)


class ImportRecord(Base):
    __tablename__ = 'imports'
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
    result: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[str] = mapped_column(String(40), default=now)


class Setting(Base):
    __tablename__ = 'settings'
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON)


class Report(Base):
    __tablename__ = 'reports'
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    title: Mapped[str] = mapped_column(String(160))
    data: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[str] = mapped_column(String(40), default=now)
