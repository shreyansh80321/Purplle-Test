from datetime import datetime
import uuid

from app.db.database import SessionLocal, Base, engine, ensure_table_columns
from app.db.models import StoreEvent


def save_event(
    store_id: str,
    camera_id: str,
    event_type: str,
    track_id: str | None = None,
    zone: str = None,
    direction: str = None,
    x: float = None,
    y: float = None,
    confidence: float = 1.0,
    timestamp: datetime | None = None,
    id_token: str | None = None,
    store_code: str | None = None,
    zone_id: str | None = None,
    zone_name: str | None = None,
    zone_type: str | None = None,
    is_revenue_zone: bool | None = None,
    is_staff: bool | None = None,
    gender_pred: str | None = None,
    gender: str | None = None,
    age_pred: str | int | None = None,
    age: str | int | None = None,
    age_bucket: str | None = None,
    group_id: str | None = None,
    group_size: int | None = None,
    queue_event_id: str | None = None,
    wait_seconds: float | None = None,
    abandoned: bool | None = None,
    queue_position_at_join: int | None = None,
    meta: dict | None = None,
):
    Base.metadata.create_all(bind=engine)
    ensure_table_columns(StoreEvent)

    db = SessionLocal()

    event_id = str(uuid.uuid4())
    normalized_timestamp = timestamp or datetime.utcnow()
    normalized_zone_id = zone_id or zone
    normalized_zone_name = zone_name or zone
    resolved_gender = gender_pred or gender
    resolved_age = age_pred if age_pred is not None else age

    event = StoreEvent(
        event_id=event_id,
        store_id=store_id,
        camera_id=camera_id,
        timestamp=normalized_timestamp,
        event_type=event_type,
        track_id=str(track_id) if track_id is not None else None,
        id_token=id_token,
        store_code=store_code or store_id,
        zone=zone,
        zone_id=normalized_zone_id,
        zone_name=normalized_zone_name,
        zone_type=zone_type,
        is_revenue_zone=is_revenue_zone,
        direction=direction,
        is_staff=is_staff,
        gender=resolved_gender,
        age=str(resolved_age) if resolved_age is not None else None,
        age_bucket=age_bucket,
        group_id=group_id,
        group_size=group_size,
        queue_event_id=queue_event_id,
        wait_seconds=wait_seconds,
        abandoned=abandoned,
        queue_position_at_join=queue_position_at_join,
        x=x,
        y=y,
        confidence=confidence,
        meta=meta or {},
    )

    db.add(event)
    db.commit()
    db.close()

    return event_id
