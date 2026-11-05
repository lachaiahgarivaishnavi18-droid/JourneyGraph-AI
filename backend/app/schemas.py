from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, Field, field_validator, model_validator

EVENT_TYPES = ['website_visit', 'product_view', 'search', 'add_to_cart', 'purchase', 'email_open', 'ad_click', 'app_open', 'support', 'return', 'review']


def utc(value):
    dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if dt.tzinfo is None:
        raise ValueError('Timestamp must include a timezone')
    return dt.astimezone(timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z')


class Credentials(BaseModel):
    email: str = Field(min_length=5, max_length=254, pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
    password: str = Field(min_length=10, max_length=128)

    @field_validator('email')
    @classmethod
    def normalize(cls, value):
        return value.strip().lower()


class CustomerInput(BaseModel):
    id: str = Field(min_length=1, max_length=80, pattern=r'^[\w-]+$')
    name: str = Field(min_length=1, max_length=160)
    email: str = Field(default='', max_length=254)
    region: str = Field(default='Unknown', max_length=80)


class EventInput(BaseModel):
    event_id: str = Field(min_length=1, max_length=80, pattern=r'^[\w-]+$')
    customer_id: str = Field(min_length=1, max_length=80, pattern=r'^[\w-]+$')
    event_type: Literal['website_visit', 'product_view', 'search', 'add_to_cart', 'purchase', 'email_open', 'ad_click', 'app_open', 'support', 'return', 'review']
    entity_id: str = Field(default='unknown', min_length=1, max_length=80)
    channel: Literal['website', 'mobile', 'email', 'ads', 'support', 'social']
    event_time: str
    valid_to: str | None = None
    properties: dict = Field(default_factory=dict)

    @field_validator('event_time', 'valid_to')
    @classmethod
    def timestamp(cls, value):
        return utc(value) if value else None

    @model_validator(mode='after')
    def interval(self):
        if self.valid_to and self.valid_to <= self.event_time:
            raise ValueError('valid_to must be later than event_time')
        if self.event_type in ('purchase', 'return'):
            amount = self.properties.get('amount', 0)
            if not isinstance(amount, (int, float)) or not 0 <= amount <= 1e9:
                raise ValueError('amount must be a finite non-negative number')
        if len(str(self.properties)) > 10000:
            raise ValueError('properties exceeds 10 KB')
        return self


class RunInput(BaseModel):
    customer_id: str | None = None
    include_predictions: bool = True


class QueryInput(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    customer_id: str | None = None


class LLMAnswer(BaseModel):
    narrative: str = Field(max_length=6000)
    evidence_ids: list[str]
    limitations: list[str]
