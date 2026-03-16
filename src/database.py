from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / 'data'
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / 'nofomo.db'
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def migrate_review_columns():
    """Add NoFOMO review columns to trades table if they don't exist."""
    review_columns = [
        ("motivation", "TEXT"),
        ("emotion", "TEXT"),
        ("lesson", "TEXT"),
        ("next_action", "TEXT"),
        ("reviewed_at", "DATETIME"),
    ]
    with engine.connect() as conn:
        existing = {row[1] for row in conn.execute(
            __import__('sqlalchemy').text("PRAGMA table_info(trades)")
        )}
        for col_name, col_type in review_columns:
            if col_name not in existing:
                conn.execute(__import__('sqlalchemy').text(
                    f"ALTER TABLE trades ADD COLUMN {col_name} {col_type}"
                ))
        conn.commit()
