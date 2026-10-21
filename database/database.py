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
    """Add category status and budget columns to existing databases."""
    columns = {
        column["name"] for column in inspect(engine).get_columns("categories")
    }
    with engine.begin() as connection:
        if "active" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE categories ADD COLUMN active "
                    "BOOLEAN NOT NULL DEFAULT TRUE"
                )
            )
        if "budget" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE categories ADD COLUMN budget "
                    "NUMERIC(10, 2) NOT NULL DEFAULT 0"
                )
            )
        connection.execute(
            text(
                "CREATE TABLE IF NOT EXISTS category_seed_state ("
                "id INTEGER PRIMARY KEY CHECK (id = 1), "
                "defaults_seeded BOOLEAN NOT NULL DEFAULT FALSE)"
            )
        )
        connection.execute(
            text(
                "INSERT OR IGNORE INTO category_seed_state (id, defaults_seeded) "
                "VALUES (1, FALSE)"
            )
        )
        seed_state_columns = {
            column["name"]
            for column in inspect(engine).get_columns("category_seed_state")
        }
        if "legacy_budgets_migrated" not in seed_state_columns:
            connection.execute(
                text(
                    "ALTER TABLE category_seed_state ADD COLUMN "
                    "legacy_budgets_migrated BOOLEAN NOT NULL DEFAULT FALSE"
                )
            )

    from model.category_model import Category

    defaults = [
        (
            "Comida y restauración",
            "Tickets y saldo virtual para comidas durante la jornada laboral.",
            "restaurant",
            "comida",
            15000,
        ),
        (
            "Transporte y movilidad",
            "Abonos y gastos de desplazamiento y transporte público.",
            "directions_bus",
            "transporte",
            12000,
        ),
        (
            "Formación profesional",
            "Cursos, conferencias y libros técnicos.",
            "school",
            "formacion",
            10000,
        ),
        (
            "Salud y bienestar",
            "Seguro médico, dental y bienestar físico.",
            "health_and_safety",
            "salud",
            8000,
        ),
        (
            "Guardería infantil",
            "Cheques y pagos directos a centros de educación infantil.",
            "child_care",
            "guarderia",
            5500,
        ),
    ]
    default_budgets_by_name = {
        name.casefold(): budget
        for name, _description, _icon, _color, budget in defaults
    }
    default_budgets_by_name.update(
        {
            "comida": 15000,
            "transporte": 12000,
            "formación": 10000,
            "formacion": 10000,
            "salud": 8000,
            "guardería": 5500,
            "guarderia": 5500,
        }
    )
    with sessionmaker(autocommit=False, autoflush=False, bind=engine)() as db:
        seeded = db.execute(
            text("SELECT defaults_seeded FROM category_seed_state WHERE id = 1")
        ).scalar()
        legacy_budgets_migrated = db.execute(
            text(
                "SELECT legacy_budgets_migrated "
                "FROM category_seed_state WHERE id = 1"
            )
        ).scalar()
        if not seeded:
            if db.query(Category.id).first() is None:
                db.add_all(
                    Category(
                        name=name,
                        icon=icon,
                        color=color,
                        budget=budget,
                        description=description,
                        active=True,
                    )
                    for name, description, icon, color, budget in defaults
                )
                db.flush()
            db.execute(
                text(
                    "UPDATE category_seed_state SET defaults_seeded = TRUE WHERE id = 1"
                )
            )
        if not legacy_budgets_migrated:
            for category in db.query(Category).all():
                default_budget = default_budgets_by_name.get(category.name.casefold())
                if default_budget is not None and not category.budget:
                    category.budget = default_budget
            db.execute(
                text(
                    "UPDATE category_seed_state SET legacy_budgets_migrated = TRUE "
                    "WHERE id = 1"
                )
            )
        if not seeded or not legacy_budgets_migrated:
            db.commit()
