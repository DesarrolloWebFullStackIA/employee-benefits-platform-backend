from typing import Generator
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker

from config.config_variables import settings

# Configure SQLite engine options
connect_args = {}
if "sqlite" in settings.DATABASE_URL:
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False,
)


# Enforce foreign key constraints in SQLite
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if "sqlite" in settings.DATABASE_URL:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator:
    """FastAPI dependency that yields a SQLAlchemy database session and closes it on exit."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all database tables defined in SQLAlchemy models."""
    import model  # noqa: F401 - Ensure models are loaded into Base metadata
    Base.metadata.create_all(bind=engine)
    _migrate_category_columns()


def _migrate_category_columns() -> None:
    """Add the active flag needed to filter the category catalog."""
    columns = {
        column["name"] for column in inspect(engine).get_columns("categories")
    }
    if "active" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE categories ADD COLUMN active "
                    "BOOLEAN NOT NULL DEFAULT TRUE"
                )
            )
