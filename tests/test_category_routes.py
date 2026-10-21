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
from model.expense_model import Expense
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
        with TestingSessionLocal() as db:
            db.add(
                Category(
                    name="Presupuesto inicial",
                    icon="category",
                    color="general",
                    budget=5000,
                )
            )
            db.commit()

        response = client.post(
            "/api/v1/categories",
            json={
                "name": "  Alimentación  ",
                "description": "Comidas durante la jornada",
                "icon": "restaurant",
                "color": "comida",
                "budget": 1800,
            },
        )
        assert response.status_code == 201
        category = response.json()
        assert category["name"] == "Alimentación"
        assert float(category["budget"]) == 1800
        assert category["active"] is True
        category_id = category["id"]

        with TestingSessionLocal() as db:
            db.query(Category).filter_by(name="Presupuesto inicial").delete()
            db.commit()

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
            db.add_all(
                [
                    Expense(
                        employee_id=employee.id,
                        category_id=category_id,
                        amount=600,
                        description="Gasto aprobado",
                        status="APPROVED",
                    ),
                    Expense(
                        employee_id=employee.id,
                        category_id=category_id,
                        amount=100,
                        description="Gasto pendiente",
                        status="PENDING",
                    ),
                    Expense(
                        employee_id=employee.id,
                        category_id=category_id,
                        amount=900,
                        description="Gasto rechazado",
                        status="REJECTED",
                    ),
                ]
            )
            db.commit()

        active_categories = client.get("/api/v1/categories").json()
        assert [item["id"] for item in active_categories] == [category_id]
        assert active_categories[0]["benefits_count"] == 1
        assert float(active_categories[0]["spent_amount"]) == 600
        assert active_categories[0]["expenses_count"] == 3
        all_categories = client.get(
            "/api/v1/categories?include_inactive=true"
        ).json()
        assert len(all_categories) == 2
        assert next(item for item in all_categories if item["name"] == "Inactiva")[
            "active"
        ] is False

        update_response = client.put(
            f"/api/v1/categories/{category_id}",
            json={"name": "Comida"},
        )
        assert update_response.status_code == 200
        assert update_response.json()["name"] == "Comida"
        assert update_response.json()["icon"] == "restaurant"
        deactivate_response = client.put(
            f"/api/v1/categories/{category_id}",
            json={"active": False, "budget": 2100},
        )
        assert deactivate_response.status_code == 200
        assert deactivate_response.json()["active"] is False
        assert float(deactivate_response.json()["budget"]) == 2100

        delete_response = client.delete(f"/api/v1/categories/{category_id}")
        assert delete_response.status_code == 409
        assert delete_response.json()["detail"] == (
            "Cannot delete category 'Comida' because it has active benefit "
            "allocations or expenses linked to it (Referential Integrity)."
        )

        unlinked_response = client.post(
            "/api/v1/categories",
            json={
                "name": "Movilidad",
                "icon": "directions_bus",
                "color": "blue",
                "budget": 100,
            },
        )
        unlinked_id = unlinked_response.json()["id"]
        assert client.delete(f"/api/v1/categories/{unlinked_id}").status_code == 204
        assert client.get(f"/api/v1/categories/{unlinked_id}").status_code == 404
    finally:
        app.dependency_overrides.clear()
        client.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_category_creation_cannot_exceed_remaining_budget():
    client, app, engine = create_test_client()
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO categories "
                    "(name, icon, color, budget, active) "
                    "VALUES ('Presupuesto base', 'category', 'general', 1000, 1)"
                )
            )
        response = client.post(
            "/api/v1/categories",
            json={
                "name": "Excede restante",
                "icon": "category",
                "color": "general",
                "budget": 1001,
            },
            headers={"X-Global-Budget-Cap": "2000"},
        )
        assert response.status_code == 422
        assert "dinero restante" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()
        client.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_category_creation_rejects_when_no_money_remains():
    client, app, engine = create_test_client()
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO categories "
                    "(name, icon, color, budget, active) "
                    "VALUES ('Presupuesto base', 'category', 'general', 1000, 1)"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO employees "
                    "(first_name, last_name, email, department, position, max_budget) "
                    "VALUES ('Ana', 'Test', 'ana.test@example.com', 'People', 'HR', 1000)"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO expenses (employee_id, category_id, amount, description, status) "
                    "VALUES (1, 1, 1000, 'Gasto total', 'APPROVED')"
                )
            )
        response = client.post(
            "/api/v1/categories",
            json={
                "name": "Sin fondos",
                "icon": "category",
                "color": "general",
                "budget": 1,
            },
            headers={"X-Global-Budget-Cap": "1000"},
        )
        assert response.status_code == 422
        assert "dinero restante" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()
        client.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_category_budget_increase_cannot_exceed_dashboard_cap():
    client, app, engine = create_test_client()
    try:
        response = client.post(
            "/api/v1/categories",
            json={
                "name": "Presupuesto inicial",
                "icon": "category",
                "color": "general",
                "budget": 900,
            },
            headers={"X-Global-Budget-Cap": "1000"},
        )
        assert response.status_code == 201
        category_id = response.json()["id"]

        update_response = client.put(
            f"/api/v1/categories/{category_id}",
            json={"budget": 1100},
            headers={"X-Global-Budget-Cap": "1000"},
        )
        assert update_response.status_code == 422
        assert "dinero restante" in update_response.json()["detail"]
    finally:
        app.dependency_overrides.clear()
        client.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_category_budget_uses_updated_dashboard_cap():
    client, app, engine = create_test_client()
    try:
        response = client.post(
            "/api/v1/categories",
            json={
                "name": "Presupuesto inicial",
                "icon": "category",
                "color": "general",
                "budget": 900,
            },
            headers={"X-Global-Budget-Cap": "1000"},
        )
        assert response.status_code == 201
        category_id = response.json()["id"]

        update_response = client.put(
            f"/api/v1/categories/{category_id}",
            json={"budget": 1100},
            headers={"X-Global-Budget-Cap": "1200"},
        )
        assert update_response.status_code == 200
        assert float(update_response.json()["budget"]) == 1100
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
        assert "budget" in column_names
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_init_db_seeds_default_categories_only_once(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    monkeypatch.setattr(database_module, "engine", engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    try:
        database_module.init_db()
        with TestingSessionLocal() as db:
            categories = db.query(Category).all()
            assert len(categories) == 5
            assert sum(float(category.budget) for category in categories) == 50500
            db.delete(categories[0])
            db.commit()

        database_module.init_db()
        with TestingSessionLocal() as db:
            assert db.query(Category).count() == 4
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_init_db_migrates_legacy_category_budgets(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    monkeypatch.setattr(database_module, "engine", engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    try:
        Base.metadata.create_all(bind=engine)
        with TestingSessionLocal() as db:
            db.add(
                Category(
                    name="Comida",
                    icon="restaurant",
                    color="comida",
                    budget=0,
                )
            )
            db.commit()

        database_module.init_db()
        with TestingSessionLocal() as db:
            category = db.query(Category).filter_by(name="Comida").one()
            assert float(category.budget) == 15000
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
