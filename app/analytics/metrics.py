from sqlalchemy.orm import Session
from app.db.models import StoreEvent


def get_store_metrics(db: Session, store_id: str = "brigade_bangalore"):
    events = db.query(StoreEvent).filter(StoreEvent.store_id == store_id).all()

    entries = [e for e in events if e.event_type == "entry"]
    exits = [e for e in events if e.event_type == "exit"]
    billing = [e for e in events if e.event_type == "billing_visit"]
    anomalies = [e for e in events if e.event_type == "anomaly"]

    entered_tracks = set(e.track_id for e in entries)
    exited_tracks = set(e.track_id for e in exits)
    billing_tracks = set(e.track_id for e in billing)

    active_sessions = len(entered_tracks - exited_tracks)
    unique_visitors = len(entered_tracks)
    estimated_conversions = len(billing_tracks)

    conversion_rate = 0.0
    if unique_visitors > 0:
        conversion_rate = round((estimated_conversions / unique_visitors) * 100, 2)

    return {
        "store_id": store_id,
        "total_entries": len(entries),
        "total_exits": len(exits),
        "active_sessions": active_sessions,
        "unique_visitors": unique_visitors,
        "billing_visits": len(billing),
        "estimated_conversions": estimated_conversions,
        "conversion_rate": conversion_rate,
        "anomaly_count": len(anomalies),
        "anomalies": [
            {
                "event_id": e.event_id,
                "track_id": e.track_id,
                "zone": e.zone,
                "reason": e.meta.get("reason") if e.meta else None,
                "severity": e.meta.get("severity") if e.meta else None,
                "timestamp": e.timestamp.isoformat()
            }
            for e in anomalies
        ]
    }