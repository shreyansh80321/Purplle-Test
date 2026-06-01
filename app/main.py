from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from app.db.database import Base, engine, get_db
from app.db.models import StoreEvent
from app.analytics.metrics import get_store_metrics
from app.analytics.funnel import get_store_funnel
from app.analytics.anomalies import get_store_anomalies

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Purplle Store Intelligence System",
    version="0.2.0",
    description="CPU-first Store Intelligence API using CCTV-derived structured events."
)


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
                "zone": e.zone,
                "direction": e.direction,
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