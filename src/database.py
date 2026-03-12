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
