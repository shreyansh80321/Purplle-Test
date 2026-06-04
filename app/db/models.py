from sqlalchemy import Boolean, Column, DateTime, Float, Integer, JSON, String
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
    track_id = Column(String, index=True, nullable=True)
    id_token = Column(String, index=True, nullable=True)
    store_code = Column(String, index=True, nullable=True)

    zone = Column(String, nullable=True)
    zone_id = Column(String, index=True, nullable=True)
    zone_name = Column(String, nullable=True)
    zone_type = Column(String, nullable=True)
    is_revenue_zone = Column(Boolean, nullable=True)
    direction = Column(String, nullable=True)
    is_staff = Column(Boolean, nullable=True)
    gender = Column(String, nullable=True)
    age = Column(String, nullable=True)
    age_bucket = Column(String, nullable=True)
    group_id = Column(String, nullable=True)
    group_size = Column(Integer, nullable=True)
    queue_event_id = Column(String, index=True, nullable=True)
    wait_seconds = Column(Float, nullable=True)
    abandoned = Column(Boolean, nullable=True)
    queue_position_at_join = Column(Integer, nullable=True)

    x = Column(Float, nullable=True)
    y = Column(Float, nullable=True)

    confidence = Column(Float, default=1.0)
    meta = Column(JSON, nullable=True)
