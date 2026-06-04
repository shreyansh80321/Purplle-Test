from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from app.db.database import Base, engine, get_db
from app.db.models import StoreEvent
from app.analytics.metrics import get_store_metrics
from app.analytics.funnel import get_store_funnel
from app.analytics.anomalies import get_store_anomalies
from app.api.video import router as video_router
from app.core.store_layout import build_semantic_layout
from app.db.database import ensure_table_columns

Base.metadata.create_all(bind=engine)
ensure_table_columns(StoreEvent)

app = FastAPI(
    title="Purplle Store Intelligence System",
    version="0.2.0",
    description="CPU-first Store Intelligence API using CCTV-derived structured events."
)

app.include_router(video_router)


@app.get("/")
def health_check():
    return {
        "status": "ok",
        "service": "store-intelligence",
        "time": datetime.utcnow().isoformat()
    }


@app.get("/metrics")
def metrics(db: Session = Depends(get_db)):
    return get_store_metrics(db)


@app.get("/funnel")
def funnel(db: Session = Depends(get_db)):
    return get_store_funnel(db)


@app.get("/events")
def events(db: Session = Depends(get_db)):
    result = (
        db.query(StoreEvent)
        .order_by(StoreEvent.timestamp.desc())
        .limit(100)
        .all()
    )

    return {
        "count": len(result),
        "events": [
            {
                "event_id": e.event_id,
                "store_id": e.store_id,
                "camera_id": e.camera_id,
                "timestamp": e.timestamp.isoformat(),
                "event_type": e.event_type,
                "track_id": e.track_id,
                "id_token": e.id_token,
                "store_code": e.store_code,
                "zone": e.zone,
                "zone_id": e.zone_id,
                "zone_name": e.zone_name,
                "zone_type": e.zone_type,
                "is_revenue_zone": e.is_revenue_zone,
                "direction": e.direction,
                "is_staff": e.is_staff,
                "gender": e.gender,
                "age": e.age,
                "age_bucket": e.age_bucket,
                "group_id": e.group_id,
                "group_size": e.group_size,
                "queue_event_id": e.queue_event_id,
                "wait_seconds": e.wait_seconds,
                "abandoned": e.abandoned,
                "queue_position_at_join": e.queue_position_at_join,
                "x": e.x,
                "y": e.y,
                "confidence": e.confidence,
                "meta": e.meta
            }
            for e in result
        ]
    }


@app.get("/anomalies")
def anomalies(db: Session = Depends(get_db)):
    return get_store_anomalies(db)


@app.get("/layout")
def layout(camera_role: str = "inside_store"):
    return build_semantic_layout(camera_role)


@app.get("/zones")
def zones(camera_role: str = "inside_store"):
    return build_semantic_layout(camera_role)


@app.delete("/events/reset")
def reset_events(db: Session = Depends(get_db)):
    deleted = db.query(StoreEvent).delete()
    db.commit()

    return {
        "status": "success",
        "deleted_events": deleted
    }
