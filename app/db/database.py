from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker, declarative_base
from pathlib import Path
from loguru import logger

DB_DIR = Path("data/processed")
DB_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{DB_DIR / 'store_intelligence.db'}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def ensure_table_columns(model):
    inspector = inspect(engine)
    table_name = model.__tablename__

    if not inspector.has_table(table_name):
        Base.metadata.create_all(bind=engine)
        return

    existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
    expected_columns = {column.name for column in model.__table__.columns}

    if expected_columns.issubset(existing_columns):
        return

    missing_columns = sorted(expected_columns - existing_columns)
    logger.warning(
        "Recreating table '{}' to align SQLite schema. Missing columns: {}",
        table_name,
        missing_columns,
    )
    model.__table__.drop(bind=engine, checkfirst=True)
    model.__table__.create(bind=engine, checkfirst=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
