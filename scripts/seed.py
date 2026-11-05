"""Generate clearly labeled synthetic data and seed an empty database."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.database import Base, engine, SessionLocal
from backend.app.data import seed_demo
from backend.app.analytics import segment_customers

Base.metadata.create_all(engine)
with SessionLocal() as db:
    print(seed_demo(db, Path(__file__).resolve().parents[1] / 'data' / 'samples'))
    segment_customers(db)
    db.commit()
