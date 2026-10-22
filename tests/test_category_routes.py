from datetime import date
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
                        concept="Gasto aprobado", date=date.today(),
                        status="APPROVED",
                    ),
                    Expense(
                        employee_id=employee.id,
                        category_id=category_id,
                        amount=100,
                        concept="Gasto pendiente", date=date.today(),
                        status="PENDING",
                    ),
                    Expense(
                        employee_id=employee.id,
                        category_id=category_id,
                        amount=900,
                        concept="Gasto rechazado", date=date.today(),
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
                    "(first_name, last_name, email, department, max_budget) "
                    "VALUES ('Ana', 'Test', 'ana.test@example.com', 'People', 1000)"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO expenses (employee_id, category_id, amount, concept, date, status) "
                    "VALUES (1, 1, 1000, 'Gasto total', '2026-01-01', 'APPROVED')"
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


def test_init_db_seeds_via_seed_py_when_empty(monkeypatch):
    import database.seed as seed_module
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    monkeypatch.setattr(database_module, "engine", engine)
    monkeypatch.setattr(seed_module, "engine", engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    monkeypatch.setattr(database_module, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(seed_module, "SessionLocal", TestingSessionLocal)
    try:
        database_module.init_db()
        with TestingSessionLocal() as db:
            categories = db.query(Category).all()
            assert len(categories) == 6
            assert any(c.name == "Comida" and c.icon == "restaurant" for c in categories)
            assert any(c.name == "Gimnasio" and c.icon == "fitness_center" for c in categories)
            assert db.query(Employee).count() == 10
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
