from sqlalchemy.orm import Session
from app.analytics.event_semantics import (
    is_billing_related,
    constrain_to_entered,
    is_non_staff,
    unique_visitor_ids,
    visitor_key,
)
from app.db.models import StoreEvent


def get_store_metrics(db: Session, store_id: str = "brigade_bangalore"):
    events = db.query(StoreEvent).filter(StoreEvent.store_id == store_id).all()

    entries = [e for e in events if e.event_type == "entry" and is_non_staff(e)]
    exits = [e for e in events if e.event_type == "exit" and is_non_staff(e)]
    billing = [e for e in events if is_billing_related(e) and is_non_staff(e)]
    anomalies = [e for e in events if e.event_type == "anomaly"]

    entered_visitors = unique_visitor_ids(entries)
    exited_visitors = constrain_to_entered(unique_visitor_ids(exits), entered_visitors)
    billing_visitors = constrain_to_entered(unique_visitor_ids(billing), entered_visitors)

    total_exits = len(exited_visitors)
    active_sessions = len(entered_visitors - exited_visitors)
    total_entries = len(entered_visitors)
    unique_visitors = total_entries
    billing_visits = len(billing_visitors)
    estimated_conversions = min(len(billing_visitors), total_entries)

    if total_entries > 0:
        billing_visits = min(billing_visits, total_entries)
    else:
        billing_visits = 0
        estimated_conversions = 0

    conversion_rate = 0.0
    if total_entries > 0:
        conversion_rate = round((estimated_conversions / total_entries) * 100, 2)
        conversion_rate = min(conversion_rate, 100.0)

    return {
        "store_id": store_id,
        "total_entries": total_entries,
        "total_exits": total_exits,
        "active_sessions": active_sessions,
        "unique_visitors": unique_visitors,
        "billing_visits": billing_visits,
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
