from sqlmodel import create_engine, SQLModel, Session
from sqlalchemy import inspect, text

DATABASE_URL = "sqlite:///./tallyus.db"

engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    _migrate()


def _migrate():
    """Add missing columns to existing tables."""
    inspector = inspect(engine)
    if "expense" in inspector.get_table_names():
        columns = [col["name"] for col in inspector.get_columns("expense")]
        if "user_id" not in columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE expense ADD COLUMN user_id VARCHAR"))


def get_session():
    with Session(engine) as session:
        yield session
