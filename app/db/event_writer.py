from datetime import datetime
import uuid

from app.db.database import SessionLocal, Base, engine
from app.db.models import StoreEvent


def save_event(
    store_id: str,
    camera_id: str,
    event_type: str,
    track_id: str,
    zone: str = None,
    direction: str = None,
    x: float = None,
    y: float = None,
    confidence: float = 1.0,
    meta: dict | None = None,
):
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    event_id = str(uuid.uuid4())

    event = StoreEvent(
        event_id=event_id,
        store_id=store_id,
        camera_id=camera_id,
        timestamp=datetime.utcnow(),
        event_type=event_type,
        track_id=str(track_id),
        zone=zone,
        direction=direction,
        x=x,
        y=y,
        confidence=confidence,
        meta=meta or {},
    )

    db.add(event)
    db.commit()
    db.close()

    return event_id