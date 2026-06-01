from sqlalchemy import Column, Integer, String, Float, DateTime, JSON
from datetime import datetime
from app.db.database import Base


class StoreEvent(Base):
    __tablename__ = "store_events"

    id = Column(Integer, primary_key=True, index=True)

    event_id = Column(String, unique=True, index=True, nullable=False)
    store_id = Column(String, index=True, nullable=False)
    camera_id = Column(String, index=True, nullable=False)

    timestamp = Column(DateTime, index=True, default=datetime.utcnow)

    event_type = Column(String, index=True, nullable=False)
    track_id = Column(String, index=True, nullable=False)

    zone = Column(String, nullable=True)
    direction = Column(String, nullable=True)

    x = Column(Float, nullable=True)
    y = Column(Float, nullable=True)

    confidence = Column(Float, default=1.0)
    meta = Column(JSON, nullable=True)