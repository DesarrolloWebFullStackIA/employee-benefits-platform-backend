import pytest

def test_expense_exceeds_balance_fails(client):
    # Crear empleado, categoría y beneficio con saldo limitado (Setup)
    emp_res = client.post("/api/v1/employees/", json={"name": "Test User", "email": "test@company.com", "department": "IT", "max_budget": 1000.0})
    emp_id = emp_res.json()["id"]
    
    cat_res = client.post("/api/v1/categories/", json={"name": "Comida", "description": "Comidas", "icon": "utensils", "badge_color": "#3B82F6"})
    cat_id = cat_res.json()["id"]

    ben_res = client.post("/api/v1/benefits/", json={"employee_id": emp_id, "category_id": cat_id, "allocated_amount": 200.0})
    ben_id = ben_res.json()["id"]

    # Registrar gasto superior al saldo asignado del beneficio (HTTP 422)
    response = client.post("/api/v1/expenses/", json={
        "benefit_id": ben_id,
        "title": "Cena cara",
        "amount": 250.0,
        "date": "2026-03-20"
    })
    assert response.status_code == 422
    assert "exceeds" in response.json()["detail"].lower() or "saldo" in response.json()["detail"].lower()

def test_approval_conditional_balance_check(client):
    # Setup
    emp_res = client.post("/api/v1/employees/", json={"name": "Ana Test", "email": "ana@company.com", "department": "HR", "max_budget": 1000.0})
    emp_id = emp_res.json()["id"]
    cat_res = client.post("/api/v1/categories/", json={"name": "Transporte", "description": "Transporte", "icon": "bus", "badge_color": "#10B981"})
    cat_id = cat_res.json()["id"]
    ben_res = client.post("/api/v1/benefits/", json={"employee_id": emp_id, "category_id": cat_id, "allocated_amount": 100.0})
    ben_id = ben_res.json()["id"]

    # Registrar gasto en estado Pendiente (el registro puede permitirse o validarse)
    exp_res = client.post("/api/v1/expenses/", json={
        "benefit_id": ben_id,
        "title": "Taxi",
        "amount": 150.0,
        "date": "2026-03-20"
    })
    exp_id = exp_res.json()["id"]

    # Intentar aprobar si excede el saldo actual (Doble validación en aprobación)
    approval_res = client.patch(f"/api/v1/expenses/{exp_id}/status", json={"status": "Approved"})
    assert approval_res.status_code == 422

def test_rejection_refunds_funds(client):
    # Setup y aprobación inicial de un gasto válido
    emp_res = client.post("/api/v1/employees/", json={"name": "Luis Test", "email": "luis@company.com", "department": "Sales", "max_budget": 1000.0})
    emp_id = emp_res.json()["id"]
    cat_res = client.post("/api/v1/categories/", json={"name": "Formación", "description": "Cursos", "icon": "book", "badge_color": "#8B5CF6"})
    cat_id = cat_res.json()["id"]
    ben_res = client.post("/api/v1/benefits/", json={"employee_id": emp_id, "category_id": cat_id, "allocated_amount": 500.0})
    ben_id = ben_res.json()["id"]

    exp_res = client.post("/api/v1/expenses/", json={
        "benefit_id": ben_id,
        "title": "Curso Python",
        "amount": 200.0,
        "date": "2026-03-20"
    })
    exp_id = exp_res.json()["id"]

    # Aprobar gasto (descuenta saldo)
    client.patch(f"/api/v1/expenses/{exp_id}/status", json={"status": "Approved"})

    # Rechazar el gasto previamente aprobado debe liberar/reembolsar el saldo
    reject_res = client.patch(f"/api/v1/expenses/{exp_id}/status", json={"status": "Rejected"})
    assert reject_res.status_code == 200

    # Verificar que el beneficio recuperó su saldo disponible
    ben_check = client.get(f"/api/v1/benefits/{ben_id}").json()
    assert ben_check["spent_amount"] == 0.0