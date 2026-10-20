import pytest

def test_update_employee_budget_success(client):
    emp_res = client.post("/api/v1/employees/", json={"name": "Budget User", "email": "budget@company.com", "department": "Dev", "max_budget": 1000.0})
    emp_id = emp_res.json()["id"]

    # PATCH exitoso del presupuesto global
    response = client.patch(f"/api/v1/employees/{emp_id}/budget", json={"max_budget": 1500.0})
    assert response.status_code == 200
    assert response.json()["max_budget"] == 1500.0

def test_reject_budget_reduction_below_committed(client):
    emp_res = client.post("/api/v1/employees/", json={"name": "Budget User 2", "email": "budget2@company.com", "department": "Dev", "max_budget": 1000.0})
    emp_id = emp_res.json()["id"]
    cat_res = client.post("/api/v1/categories/", json={"name": "Salud", "description": "Seguro", "icon": "heart", "badge_color": "#EF4444"})
    cat_id = cat_res.json()["id"]

    # Asignar beneficio de 600€
    client.post("/api/v1/benefits/", json={"employee_id": emp_id, "category_id": cat_id, "allocated_amount": 600.0})

    # Intentar reducir el max_budget global por debajo de los beneficios asignados (HTTP 422)
    response = client.patch(f"/api/v1/employees/{emp_id}/budget", json={"max_budget": 400.0})
    assert response.status_code == 422