from sqlalchemy.orm import Session
from app.db.models import StoreEvent


def get_store_anomalies(db: Session, store_id: str = "brigade_bangalore"):
    anomalies = (
        db.query(StoreEvent)
        .filter(StoreEvent.store_id == store_id)
        .filter(StoreEvent.event_type == "anomaly")
        .order_by(StoreEvent.timestamp.desc())
        .all()
    )

    return {
        "count": len(anomalies),
        "anomalies": [
            {
                "event_id": e.event_id,
                "track_id": e.track_id,
                "zone": e.zone,
                "timestamp": e.timestamp.isoformat(),
                "reason": e.meta.get("reason") if e.meta else None,
                "severity": e.meta.get("severity") if e.meta else None
            }
            for e in anomalies
        ]
    }