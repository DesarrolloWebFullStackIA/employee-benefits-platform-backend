"""
Pluxee Enterprise HR Suite - Database Seeder
Populates the SQLite database (db.sqlite3) with realistic test fixtures
matching SQLAlchemy models, business logic constraints, and traffic light tiers.

Usage:
    python database/seed.py
"""

import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

# Fix Windows console encoding for UTF-8
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure project root is in python path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from database.database import Base, SessionLocal, engine
from model.benefit_model import Benefit
from model.category_model import Category
from model.company_model import Company
from model.employee_model import Employee
from model.expense_model import Expense


def seed_database():
    print("[*] Iniciando el proceso de seeding de la base de datos...")

    # 1. Recrear el esquema completo para aplicar actualizaciones de modelos
    print("[*] Recreando esquema de base de datos via SQLAlchemy metadata...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # 2. Poblar Presupuesto Global de la Compañía (Company)
        print("[+] Configurando presupuesto corporativo global...")
        company = Company(
            id=1,
            global_budget=Decimal("75000.00")
        )
        db.add(company)
        db.commit()

        # 3. Poblar Categorías con Presupuestos en miles de euros (5.000 - 15.000 €)
        print("[+] Insertando categorías de beneficios con presupuestos entre 5.000 y 15.000 EUR...")
        categories_data = [
            Category(
                id=1,
                name="Comida",
                description="Ayuda para comidas diarias y tickets restaurante",
                icon="utensils",
                color="#3B82F6",
                budget=Decimal("15000.00"),
                active=True,
            ),
            Category(
                id=2,
                name="Transporte",
                description="Gastos de desplazamiento urbano y transporte público",
                icon="bus",
                color="#10B981",
                budget=Decimal("12000.00"),
                active=True,
            ),
            Category(
                id=3,
                name="Formación",
                description="Cursos técnicos, certificaciones y libros",
                icon="book-open",
                color="#8B5CF6",
                budget=Decimal("10000.00"),
                active=True,
            ),
            Category(
                id=4,
                name="Salud",
                description="Seguro médico privado y bienestar físico",
                icon="heart-pulse",
                color="#EF4444",
                budget=Decimal("8000.00"),
                active=True,
            ),
            Category(
                id=5,
                name="Guardería",
                description="Cheques guardería y conciliación familiar",
                icon="baby",
                color="#F59E0B",
                budget=Decimal("6000.00"),
                active=True,
            ),
            Category(
                id=6,
                name="Gimnasio",
                description="Cuotas de centros deportivos y suscripciones fitness",
                icon="dumbbell",
                color="#EC4899",
                budget=Decimal("5000.00"),
                active=True,
            ),
        ]
        db.add_all(categories_data)
        db.commit()

        # 4. Poblar Empleados (SOLO departamentos: Tecnología, Marketing, RRHH, Ventas - SIN position)
        print("[+] Registrando empleados en departamentos exclusivos (Tecnología, Marketing, RRHH, Ventas)...")
        employees_data = [
            Employee(
                id=1,
                first_name="Ana",
                last_name="Gómez",
                email="ana.gomez@company.com",
                department="Tecnología",
                max_budget=Decimal("2500.00"),
            ),
            Employee(
                id=2,
                first_name="Carlos",
                last_name="Ruiz",
                email="carlos.ruiz@company.com",
                department="Tecnología",
                max_budget=Decimal("1800.00"),
            ),
            Employee(
                id=3,
                first_name="Elena",
                last_name="Torres",
                email="elena.torres@company.com",
                department="Marketing",
                max_budget=Decimal("1200.00"),
            ),
            Employee(
                id=4,
                first_name="David",
                last_name="Martí",
                email="david.marti@company.com",
                department="Ventas",
                max_budget=Decimal("2000.00"),
            ),
            Employee(
                id=5,
                first_name="Sofía",
                last_name="Benítez",
                email="sofia.benitez@company.com",
                department="RRHH",
                max_budget=Decimal("1500.00"),
            ),
            Employee(
                id=6,
                first_name="Javier",
                last_name="López",
                email="javier.lopez@company.com",
                department="Tecnología",
                max_budget=Decimal("2200.00"),
            ),
            Employee(
                id=7,
                first_name="Lucía",
                last_name="Ramos",
                email="lucia.ramos@company.com",
                department="Ventas",
                max_budget=Decimal("1000.00"),
            ),
            Employee(
                id=8,
                first_name="Miguel Ángel",
                last_name="Sanz",
                email="miguel.sanz@company.com",
                department="Marketing",
                max_budget=Decimal("800.00"),
            ),
            Employee(
                id=9,
                first_name="Carmen",
                last_name="Vega",
                email="carmen.vega@company.com",
                department="RRHH",
                max_budget=Decimal("1400.00"),
            ),
            Employee(
                id=10,
                first_name="Pablo",
                last_name="Navarro",
                email="pablo.navarro@company.com",
                department="Ventas",
                max_budget=Decimal("600.00"),
            ),
        ]
        db.add_all(employees_data)
        db.commit()

        # 5. Asignar Beneficios por Empleado respetando max_budget
        print("[+] Creando asignaciones de beneficios individuales...")
        benefits_data = [
            # Ana Gómez (Max: 2500) - Tecnología
            Benefit(id=1, employee_id=1, category_id=1, allocated_amount=Decimal("1000.00"), spent_amount=Decimal("0.00")), # Comida
            Benefit(id=2, employee_id=1, category_id=3, allocated_amount=Decimal("1200.00"), spent_amount=Decimal("0.00")), # Formación
            # Carlos Ruiz (Max: 1800) - Tecnología
            Benefit(id=3, employee_id=2, category_id=1, allocated_amount=Decimal("800.00"), spent_amount=Decimal("0.00")),  # Comida
            Benefit(id=4, employee_id=2, category_id=2, allocated_amount=Decimal("900.00"), spent_amount=Decimal("0.00")),  # Transporte
            # Elena Torres (Max: 1200) - Marketing
            Benefit(id=5, employee_id=3, category_id=2, allocated_amount=Decimal("500.00"), spent_amount=Decimal("0.00")),  # Transporte
            Benefit(id=6, employee_id=3, category_id=5, allocated_amount=Decimal("600.00"), spent_amount=Decimal("0.00")),  # Guardería
            # David Martí (Max: 2000) - Ventas
            Benefit(id=7, employee_id=4, category_id=1, allocated_amount=Decimal("1000.00"), spent_amount=Decimal("0.00")), # Comida
            Benefit(id=8, employee_id=4, category_id=4, allocated_amount=Decimal("900.00"), spent_amount=Decimal("0.00")),  # Salud
            # Sofía Benítez (Max: 1500) - RRHH
            Benefit(id=9, employee_id=5, category_id=3, allocated_amount=Decimal("1000.00"), spent_amount=Decimal("0.00")), # Formación
            # Javier López (Max: 2200) - Tecnología
            Benefit(id=10, employee_id=6, category_id=1, allocated_amount=Decimal("1000.00"), spent_amount=Decimal("0.00")),# Comida
            # Lucía Ramos (Max: 1000) - Ventas
            Benefit(id=11, employee_id=7, category_id=1, allocated_amount=Decimal("900.00"), spent_amount=Decimal("0.00")), # Comida
            # Miguel Ángel Sanz (Max: 800) - Marketing
            Benefit(id=12, employee_id=8, category_id=6, allocated_amount=Decimal("700.00"), spent_amount=Decimal("0.00")), # Gimnasio
            # Carmen Vega (Max: 1400) - RRHH
            Benefit(id=13, employee_id=9, category_id=2, allocated_amount=Decimal("1200.00"), spent_amount=Decimal("0.00")),# Transporte
            # Pablo Navarro (Max: 600) - Ventas
            Benefit(id=14, employee_id=10, category_id=1, allocated_amount=Decimal("550.00"), spent_amount=Decimal("0.00")),# Comida
        ]
        db.add_all(benefits_data)
        db.commit()

        # 6. Registrar Gastos con Estados (Expense)
        print("[+] Registrando gastos historicos, pendientes y aprobados...")
        now = datetime.now(timezone.utc)
        expenses_data = [
            # 1. Ana Gómez - Comida (Asignado: 1000) -> Gasto 250 -> Verde (25%)
            Expense(employee_id=1, category_id=1, amount=Decimal("250.00"), concept="Almuerzos de equipo marzo", status="APPROVED", date=(now - timedelta(days=20)).date(), receipt_type="pdf", receipt_url="#"),
            # 2. Ana Gómez - Formación (Asignado: 1200) -> Gasto 1150 -> Rojo (95.8%)
            Expense(employee_id=1, category_id=3, amount=Decimal("1150.00"), concept="Certificacion Cloud Solutions Architect", status="APPROVED", date=(now - timedelta(days=18)).date(), receipt_type="pdf", receipt_url="#"),

            # 3. Carlos Ruiz - Comida (Asignado: 800) -> Gasto 450 -> Amarillo (56.2%)
            Expense(employee_id=2, category_id=1, amount=Decimal("450.00"), concept="Menus semanales cafeteria", status="APPROVED", date=(now - timedelta(days=15)).date(), receipt_type="pdf", receipt_url="#"),
            # 4. Carlos Ruiz - Transporte (Asignado: 900) -> 200 Pendiente
            Expense(employee_id=2, category_id=2, amount=Decimal("200.00"), concept="Abono Transporte trimestral", status="PENDING", date=(now - timedelta(days=5)).date(), receipt_type="image", receipt_url="#"),

            # 5. Elena Torres - Transporte (Asignado: 500) -> Gasto 150 -> Verde (30%)
            Expense(employee_id=3, category_id=2, amount=Decimal("150.00"), concept="Bono mensual metro y cercanias", status="APPROVED", date=(now - timedelta(days=12)).date(), receipt_type="pdf", receipt_url="#"),
            # 6. Elena Torres - Guardería (Asignado: 600) -> Gasto 100 Rechazado
            Expense(employee_id=3, category_id=5, amount=Decimal("100.00"), concept="Material escolar no subvencionado", status="REJECTED", date=(now - timedelta(days=10)).date(), receipt_type="pdf", receipt_url="#", rejection_reason="Gasto no subvencionable según política"),

            # 7. David Martí - Comida (Asignado: 1000) -> Gasto 850 -> Rojo (85%)
            Expense(employee_id=4, category_id=1, amount=Decimal("850.00"), concept="Catering almuerzo clientes corporativos", status="APPROVED", date=(now - timedelta(days=8)).date(), receipt_type="pdf", receipt_url="#"),
            # 8. David Martí - Salud (Asignado: 900) -> Gasto 350 Pendiente
            Expense(employee_id=4, category_id=4, amount=Decimal("350.00"), concept="Rehabilitacion y fisioterapia postural", status="PENDING", date=(now - timedelta(days=4)).date(), receipt_type="image", receipt_url="#"),

            # 9. Sofía Benítez - Formación (Asignado: 1000) -> Gasto 500 -> Amarillo (50%)
            Expense(employee_id=5, category_id=3, amount=Decimal("500.00"), concept="Seminario People Analytics & HR Trends", status="APPROVED", date=(now - timedelta(days=7)).date(), receipt_type="pdf", receipt_url="#"),

            # 10. Javier López - Comida (Asignado: 1000) -> Gasto 300 -> Verde (30%)
            Expense(employee_id=6, category_id=1, amount=Decimal("300.00"), concept="Comidas de trabajo oficina", status="APPROVED", date=(now - timedelta(days=6)).date(), receipt_type="pdf", receipt_url="#"),

            # 11. Lucía Ramos - Comida (Asignado: 900) -> Gasto 750 -> Rojo (83.3%)
            Expense(employee_id=7, category_id=1, amount=Decimal("750.00"), concept="Restaurante auditoria anual", status="APPROVED", date=(now - timedelta(days=5)).date(), receipt_type="pdf", receipt_url="#"),

            # 12. Miguel Ángel Sanz - Gimnasio (Asignado: 700) -> Gasto 350 -> Amarillo (50%)
            Expense(employee_id=8, category_id=6, amount=Decimal("350.00"), concept="Cuota semestral gimnasio GoFit", status="APPROVED", date=(now - timedelta(days=9)).date(), receipt_type="pdf", receipt_url="#"),

            # 13. Carmen Vega - Transporte (Asignado: 1200) -> Gasto 380 -> Verde (31.6%)
            Expense(employee_id=9, category_id=2, amount=Decimal("380.00"), concept="Parking mensual sede corporativa", status="APPROVED", date=(now - timedelta(days=11)).date(), receipt_type="pdf", receipt_url="#"),

            # 14. Pablo Navarro - Comida (Asignado: 550) -> Gasto 480 -> Rojo (87.2%)
            Expense(employee_id=10, category_id=1, amount=Decimal("480.00"), concept="Restaurante menu del dia turnos", status="APPROVED", date=(now - timedelta(days=3)).date(), receipt_type="pdf", receipt_url="#"),

            # Gastos Pendientes adicionales
            Expense(employee_id=1, category_id=1, amount=Decimal("120.00"), concept="Cena de bienvenida nuevos ingresos", status="PENDING", date=(now - timedelta(days=2)).date(), receipt_type="pdf", receipt_url="#"),
            Expense(employee_id=3, category_id=2, amount=Decimal("45.00"), concept="Taxi de urgencia estacion", status="PENDING", date=(now - timedelta(days=1)).date(), receipt_type="image", receipt_url="#"),
            Expense(employee_id=5, category_id=3, amount=Decimal("40.00"), concept="Libro Clean Architecture", status="PENDING", date=(now - timedelta(hours=14)).date(), receipt_type="pdf", receipt_url="#"),
            Expense(employee_id=6, category_id=1, amount=Decimal("35.00"), concept="Cafe reunion de sprint", status="PENDING", date=(now - timedelta(hours=6)).date(), receipt_type="image", receipt_url="#"),

            # Gastos Rechazados adicionales
            Expense(employee_id=1, category_id=3, amount=Decimal("180.00"), concept="Compra periferico ergonomico", status="REJECTED", date=(now - timedelta(days=14)).date(), receipt_type="pdf", receipt_url="#", rejection_reason="Periférico no incluido en catálogo de formación"),
            Expense(employee_id=4, category_id=1, amount=Decimal("95.00"), concept="Ocio personal fin de semana", status="REJECTED", date=(now - timedelta(days=13)).date(), receipt_type="image", receipt_url="#", rejection_reason="Gasto en día no laborable"),
            Expense(employee_id=7, category_id=1, amount=Decimal("250.00"), concept="Billete de tren viaje privado", status="REJECTED", date=(now - timedelta(days=12)).date(), receipt_type="pdf", receipt_url="#", rejection_reason="Viaje de índole personal sin justificación corporativa"),
        ]
        db.add_all(expenses_data)
        db.commit()

        # 7. Sincronizar spent_amount en Benefits basándose en gastos 'approved'
        print("[*] Sincronizando acumuladores de gasto en beneficios...")
        benefits = db.query(Benefit).all()
        for b in benefits:
            approved_total = (
                db.query(Expense)
                .filter(
                    Expense.employee_id == b.employee_id,
                    Expense.category_id == b.category_id,
                    Expense.status.in_(["approved", "APPROVED"])
                )
                .all()
            )
            b.spent_amount = sum((exp.amount for exp in approved_total), Decimal("0.00"))
        db.commit()

        # 8. Resumen final de la base de datos
        emp_count = db.query(Employee).count()
        cat_count = db.query(Category).count()
        ben_count = db.query(Benefit).count()
        exp_count = db.query(Expense).count()
        approved_exp = db.query(Expense).filter(Expense.status.in_(["approved", "APPROVED"])).count()
        pending_exp = db.query(Expense).filter(Expense.status.in_(["pending", "PENDING"])).count()
        rejected_exp = db.query(Expense).filter(Expense.status.in_(["rejected", "REJECTED"])).count()
        total_spent = sum((e.amount for e in db.query(Expense).filter(Expense.status.in_(["approved", "APPROVED"])).all()), Decimal("0.00"))

        print("\n" + "=" * 64)
        print("[OK] BASE DE DATOS POBLADA EXITOSAMENTE (db.sqlite3)")
        print("=" * 64)
        print(f"[*] Presupuesto Global    : {company.global_budget:,.2f} EUR")
        print(f"[*] Categorías Catálogo   : {cat_count} (Presupuestos entre 5.000 y 15.000 EUR)")
        for cat in db.query(Category).all():
            print(f"    - {cat.name:12}: {cat.budget:,.2f} EUR")
        print(f"[*] Empleados Activos     : {emp_count}")
        dept_summary = {}
        for emp in db.query(Employee).all():
            dept_summary[emp.department] = dept_summary.get(emp.department, 0) + 1
        for dept, count in dept_summary.items():
            print(f"    - {dept:12}: {count} empleados")
        print(f"[*] Beneficios Asignados  : {ben_count}")
        print(f"[*] Total Gastos          : {exp_count} (Aprobados: {approved_exp}, Pendientes: {pending_exp}, Rechazados: {rejected_exp})")
        print(f"[*] Gasto Total Ejecutado : {total_spent:,.2f} EUR ({float(total_spent / company.global_budget * 100):.1f}% del presupuesto)")
        print("[*] Semáforos activados   : Verde (<=33%), Amarillo (33-66%), Rojo (>66%)")
        print("=" * 64 + "\n")

    except Exception as e:
        db.rollback()
        print(f"[!] Error durante el seeding de la base de datos: {e}")
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
