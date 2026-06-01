from datetime import datetime, timedelta
from app.db.database import Base, engine, SessionLocal
from app.db.models import StoreEvent
import uuid


def make_event(
    store_id,
    camera_id,
    event_type,
    track_id,
    minutes_offset,
    zone=None,
    direction=None,
    x=None,
    y=None,
    confidence=1.0,
    meta=None
):
    return StoreEvent(
        event_id=str(uuid.uuid4()),
        store_id=store_id,
        camera_id=camera_id,
        event_type=event_type,
        track_id=track_id,
        timestamp=datetime.utcnow() + timedelta(minutes=minutes_offset),
        zone=zone,
        direction=direction,
        x=x,
        y=y,
        confidence=confidence,
        meta=meta or {}
    )


def seed_demo_events():
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    existing = db.query(StoreEvent).count()
    if existing > 0:
        db.close()
        return

    events = [
        make_event("brigade_bangalore", "cam_entrance", "entry", "T001", 0, zone="entrance", direction="in", x=120, y=400),
        make_event("brigade_bangalore", "cam_floor", "zone_visit", "T001", 2, zone="lipstick_section", x=340, y=250),
        make_event("brigade_bangalore", "cam_billing", "billing_visit", "T001", 8, zone="billing", x=610, y=220),
        make_event("brigade_bangalore", "cam_entrance", "exit", "T001", 12, zone="exit", direction="out", x=130, y=410),

        make_event("brigade_bangalore", "cam_entrance", "entry", "T002", 3, zone="entrance", direction="in", x=125, y=390),
        make_event("brigade_bangalore", "cam_floor", "zone_visit", "T002", 5, zone="skincare_section", x=300, y=260),
        make_event("brigade_bangalore", "cam_entrance", "exit", "T002", 9, zone="exit", direction="out", x=140, y=415),

        make_event("brigade_bangalore", "cam_entrance", "entry", "T003", 6, zone="entrance", direction="in", x=128, y=405),
        make_event("brigade_bangalore", "cam_entrance", "re_entry", "T003", 14, zone="entrance", direction="in", x=129, y=402),

        make_event("brigade_bangalore", "cam_floor", "possible_staff", "S001", 1, zone="billing", x=600, y=220, meta={"reason": "long_duration_repeated_zone_presence"}),

        make_event("brigade_bangalore", "cam_floor", "anomaly", "A001", 15, zone="entrance", meta={"reason": "entry_exit_mismatch", "severity": "medium"}),
    ]

    db.add_all(events)
    db.commit()
    db.close()


if __name__ == "__main__":
    seed_demo_events()
    print("Demo events seeded successfully.")