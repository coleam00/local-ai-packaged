from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import settings
import os

# Ensure data directory exists
db_path = settings.DATABASE_URL.replace("sqlite:///", "")
if db_path.startswith("./"):
    db_path = db_path[2:]
db_dir = os.path.dirname(db_path)
if db_dir:
    os.makedirs(db_dir, exist_ok=True)

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False}  # SQLite specific
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Dependency for getting database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Create all tables."""
    Base.metadata.create_all(bind=engine)
    # Run migrations for existing databases
    run_migrations()


def run_migrations():
    """Run database migrations for schema changes."""
    inspector = inspect(engine)

    # Migration: Add port_overrides_json column to stack_config
    if 'stack_config' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('stack_config')]
        if 'port_overrides_json' not in columns:
            with engine.connect() as conn:
                conn.execute(text(
                    "ALTER TABLE stack_config ADD COLUMN port_overrides_json TEXT DEFAULT '{}'"
                ))
                conn.commit()
