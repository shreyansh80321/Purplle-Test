import argparse
import json
from pathlib import Path

from app.db.database import Base, SessionLocal, engine, ensure_table_columns
from app.db.models import StoreEvent


ENTRY_EXIT_EVENTS = {"entry", "exit"}
ZONE_EVENTS = {"zone_entered", "zone_exited", "zone_visit"}
QUEUE_EVENTS = {"billing_visit", "queue_completed", "queue_abandoned"}


def _isoformat(value):
    return value.isoformat() if value is not None else None


def _meta_value(event, key):
    meta = event.meta or {}
    return meta.get(key)


def _base_event_payload(event):
    return {
        "event_type": event.event_type,
        "track_id": event.track_id,
        "store_id": event.store_id,
        "camera_id": event.camera_id,
    }


def event_to_jsonl_record(event):
    timestamp = _isoformat(event.timestamp)
    record = _base_event_payload(event)

    if event.event_type in ENTRY_EXIT_EVENTS:
        record.update(
            {
                "id_token": event.id_token,
                "store_code": event.store_code or event.store_id,
                "event_timestamp": timestamp,
                "is_staff": event.is_staff,
                "gender_pred": event.gender,
                "age_pred": event.age,
                "age_bucket": event.age_bucket,
                "is_face_hidden": _meta_value(event, "is_face_hidden"),
                "group_id": event.group_id,
                "group_size": event.group_size,
            }
        )
    elif event.event_type in ZONE_EVENTS:
        record.update(
            {
                "zone_id": event.zone_id or event.zone,
                "zone_name": event.zone_name,
                "zone_type": event.zone_type,
                "is_revenue_zone": event.is_revenue_zone,
                "event_time": timestamp,
                "zone_hotspot_x": event.x,
                "zone_hotspot_y": event.y,
                "gender": event.gender,
                "age": event.age,
                "age_bucket": event.age_bucket,
            }
        )
    elif event.event_type in QUEUE_EVENTS:
        queue_timestamp = _meta_value(event, "queue_join_ts") or timestamp
        served_timestamp = _meta_value(event, "queue_served_ts")
        exit_timestamp = _meta_value(event, "queue_exit_ts")
        record.update(
            {
                "queue_event_id": event.queue_event_id,
                "zone_id": event.zone_id or event.zone,
                "zone_name": event.zone_name,
                "zone_type": event.zone_type,
                "is_revenue_zone": event.is_revenue_zone,
                "queue_join_ts": queue_timestamp,
                "queue_served_ts": served_timestamp,
                "queue_exit_ts": exit_timestamp,
                "wait_seconds": event.wait_seconds,
                "abandoned": event.abandoned,
                "queue_position_at_join": event.queue_position_at_join,
                "gender": event.gender,
                "age": event.age,
                "age_bucket": event.age_bucket,
                "zone_hotspot_x": event.x,
                "zone_hotspot_y": event.y,
            }
        )

    extra_meta = event.meta or {}
    if extra_meta:
        record["meta"] = extra_meta

    return record


def export_events_jsonl(output_path: str = "outputs/event_log.jsonl"):
    Base.metadata.create_all(bind=engine)
    ensure_table_columns(StoreEvent)

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    db = SessionLocal()
    try:
        events = (
            db.query(StoreEvent)
            .order_by(StoreEvent.timestamp.asc(), StoreEvent.id.asc())
            .all()
        )
    finally:
        db.close()

    with path.open("w", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event_to_jsonl_record(event), ensure_ascii=True))
            handle.write("\n")

    print(f"Exported {len(events)} events to {path}")
    return len(events), path


def main():
    parser = argparse.ArgumentParser(
        description="Export StoreEvent records from SQLite to JSONL."
    )
    parser.add_argument(
        "--output",
        default="outputs/event_log.jsonl",
        help="Output JSONL path.",
    )
    args = parser.parse_args()
    export_events_jsonl(output_path=args.output)


if __name__ == "__main__":
    main()
