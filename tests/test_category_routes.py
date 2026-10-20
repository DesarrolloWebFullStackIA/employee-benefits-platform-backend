from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import database.database as database_module
from database.database import Base, get_db
from model.benefit_model import Benefit
from model.category_model import Category
from model.employee_model import Employee
from routes.category_routes import router


def create_test_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=engine
    )
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), app, engine


def test_category_crud_and_name_conflict():
    client, app, engine = create_test_client()
    TestingSessionLocal = sessionmaker(bind=engine)
    try:
        response = client.post(
            "/api/v1/categories",
            json={
                "name": "  Alimentación  ",
                "description": "Comidas durante la jornada",
                "icon": "restaurant",
                "color": "comida",
            },
        )
        assert response.status_code == 201
        category = response.json()
        assert category["name"] == "Alimentación"
        category_id = category["id"]

        assert client.get("/api/v1/categories").json() == [category]
        assert client.get(f"/api/v1/categories/{category_id}").json() == category

        duplicate_response = client.post(
            "/api/v1/categories",
            json={
                "name": "ALIMENTACIÓN",
                "icon": "restaurant",
                "color": "comida",
            },
        )
        assert duplicate_response.status_code == 409
        assert duplicate_response.json()["detail"] == (
            "Category with name 'ALIMENTACIÓN' already exists"
        )

        with TestingSessionLocal() as db:
            db.add(
                Category(
                    name="Inactiva",
                    icon="category",
                    color="general",
                    active=False,
                )
            )
            employee = Employee(
                first_name="Ana",
                last_name="García",
                email="ana@example.com",
                department="People",
                position="HR",
            )
            db.add(employee)
            db.flush()
            db.add(Benefit(employee_id=employee.id, category_id=category_id))
            db.commit()

        active_categories = client.get("/api/v1/categories").json()
        assert [item["id"] for item in active_categories] == [category_id]
        assert active_categories[0]["benefits_count"] == 1

        update_response = client.put(
            f"/api/v1/categories/{category_id}",
            json={"name": "Comida"},
        )
        assert update_response.status_code == 200
        assert update_response.json()["name"] == "Comida"
        assert update_response.json()["icon"] == "restaurant"

        delete_response = client.delete(f"/api/v1/categories/{category_id}")
        assert delete_response.status_code == 409
        assert delete_response.json()["detail"] == (
            "Cannot delete category 'Comida' because it has active benefit "
            "allocations or expenses linked to it (Referential Integrity)."
        )

        unlinked_response = client.post(
            "/api/v1/categories",
            json={"name": "Movilidad", "icon": "directions_bus", "color": "blue"},
        )
        unlinked_id = unlinked_response.json()["id"]
        assert client.delete(f"/api/v1/categories/{unlinked_id}").status_code == 204
        assert client.get(f"/api/v1/categories/{unlinked_id}").status_code == 404
    finally:
        app.dependency_overrides.clear()
        client.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_init_db_migrates_existing_category_table(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE categories ("
                "id INTEGER PRIMARY KEY, "
                "name VARCHAR(100) NOT NULL UNIQUE, "
                "description VARCHAR(255), "
                "icon VARCHAR(100), "
                "color VARCHAR(50), "
                "created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            )
        )

    monkeypatch.setattr(database_module, "engine", engine)
    try:
        database_module.init_db()
        column_names = {
            column["name"] for column in inspect(engine).get_columns("categories")
        }
        assert "active" in column_names
        assert "budget" not in column_names
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
