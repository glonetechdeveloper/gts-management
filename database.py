import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:Preserved28/4@localhost:5432/GlonetechManagementSuiteDataBase",
)

engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    """Create all database tables from SQLAlchemy models."""
    Base.metadata.create_all(bind=engine)
