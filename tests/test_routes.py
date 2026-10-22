import pytest

def test_unique_category_per_employee_constraint(client):
    emp_res = client.post("/api/v1/employees/", json={"name": "Unique User", "email": "unique@company.com", "department": "QA", "max_budget": 2000.0})
    emp_id = emp_res.json()["id"]
    cat_res = client.post("/api/v1/categories/", json={"name": "Gimnasio", "description": "Gym", "icon": "dumbbell", "badge_color": "#EC4899"})
    cat_id = cat_res.json()["id"]

    # Primera asignación exitosa
    res1 = client.post("/api/v1/benefits/", json={"employee_id": emp_id, "category_id": cat_id, "allocated_amount": 500.0})
    assert res1.status_code == 200

    # Segunda asignación de la misma categoría al mismo empleado debe fallar (HTTP 409 o 422)
    res2 = client.post("/api/v1/benefits/", json={"employee_id": emp_id, "category_id": cat_id, "allocated_amount": 300.0})
    assert res2.status_code in [409, 422]

def test_dashboard_kpis_and_filters(client):
    # Validar que el endpoint del dashboard responde correctamente y los filtros devuelven datos
    dashboard_res = client.get("/api/v1/dashboard/summary")
    assert dashboard_res.status_code == 200
    assert "total_allocated" in dashboard_res.json() or "employees_count" in dashboard_res.json()

    expenses_res = client.get("/api/v1/expenses?status=Approved")
    assert expenses_res.status_code == 200
    assert isinstance(expenses_res.json(), list)