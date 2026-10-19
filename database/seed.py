import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'app.db')

def seed_database():
    print("🌱 Iniciando el proceso de seeding de la base de datos...")
    
    # Asegurar que el directorio existe
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Iniciar transacción
        conn.execute("BEGIN TRANSACTION;")

        # 0. Limpiar datos previos para garantizar idempotencia (US-BE-03.5)
        cursor.executescript("""
            DROP TABLE IF EXISTS expenses;
            DROP TABLE IF EXISTS benefits;
            DROP TABLE IF EXISTS employees;
            DROP TABLE IF EXISTS categories;
        """)

        # 1. Crear Esquema Relacional
        cursor.executescript("""
            CREATE TABLE categories (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                icon TEXT,
                badge_color TEXT
            );

            CREATE TABLE employees (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                department TEXT NOT NULL,
                max_budget REAL NOT NULL
            );

            CREATE TABLE benefits (
                id TEXT PRIMARY KEY,
                employee_id TEXT,
                category_id TEXT,
                allocated_amount REAL NOT NULL,
                spent_amount REAL DEFAULT 0,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
                FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
                UNIQUE(employee_id, category_id)
            );

            CREATE TABLE expenses (
                id TEXT PRIMARY KEY,
                benefit_id TEXT,
                title TEXT NOT NULL,
                description TEXT,
                amount REAL NOT NULL,
                date TEXT NOT NULL,
                status TEXT CHECK(status IN ('Pending', 'Approved', 'Rejected')) NOT NULL,
                FOREIGN KEY (benefit_id) REFERENCES benefits(id) ON DELETE CASCADE
            );
        """)

        # 2. Insertar Categorías (AC-BE-03.3)
        categories_data = [
            ('cat-1', 'Comida', 'Ayuda para comidas diarias', 'utensils', '#3B82F6'),
            ('cat-2', 'Transporte', 'Gastos de desplazamiento y transporte público', 'bus', '#10B981'),
            ('cat-3', 'Guardería', 'Cheques guardería y cuidado infantil', 'baby', '#F59E0B'),
            ('cat-4', 'Formación', 'Cursos, conferencias y libros técnicos', 'book-open', '#8B5CF6'),
            ('cat-5', 'Salud', 'Seguro médico y bienestar físico', 'heart-pulse', '#EF4444'),
            ('cat-6', 'Gimnasio', 'Cuotas de gimnasio y centros deportivos', 'dumbbell', '#EC4899')
        ]
        cursor.executemany("INSERT INTO categories VALUES (?, ?, ?, ?, ?)", categories_data)

        # 3. Insertar Empleados (AC-BE-03.2) - 10 empleados con presupuestos entre 500€ y 2500€
        employees_data = [
            ('emp-1', 'Ana Gómez', 'ana.gomez@company.com', 'Engineering', 2500.0),
            ('emp-2', 'Carlos Ruiz', 'carlos.ruiz@company.com', 'Product', 1800.0),
            ('emp-3', 'Elena Torres', 'elena.torres@company.com', 'Marketing', 1200.0),
            ('emp-4', 'David Martí', 'david.marti@company.com', 'Sales', 2000.0),
            ('emp-5', 'Sofía Benítez', 'sofia.benitez@company.com', 'HR', 1500.0),
            ('emp-6', 'Javier López', 'javier.lopez@company.com', 'Engineering', 2200.0),
            ('emp-7', 'Lucía Ramos', 'lucia.ramos@company.com', 'Finance', 1000.0),
            ('emp-8', 'Miguel Ángel Sanz', 'miguel.sanz@company.com', 'Design', 800.0),
            ('emp-9', 'Carmen Vega', 'carmen.vega@company.com', 'Legal', 1400.0),
            ('emp-10', 'Pablo Navarro', 'pablo.navarro@company.com', 'Support', 600.0)
        ]
        cursor.executemany("INSERT INTO employees VALUES (?, ?, ?, ?, ?)", employees_data)

        # 4. Generar Asignaciones de Beneficios respetando max_budget (AC-BE-03.4)
        # Relacionamos empleados con categorías específicas y importes que suman <= max_budget
        benefits_data = [
            # Ana Gómez (Max: 2500) -> Verde / Rojo
            ('ben-1', 'emp-1', 'cat-1', 1000.0, 0.0), # Comida
            ('ben-2', 'emp-1', 'cat-4', 1200.0, 0.0), # Formación
            # Carlos Ruiz (Max: 1800) -> Ámbar
            ('ben-3', 'emp-2', 'cat-1', 800.0, 0.0),
            ('ben-4', 'emp-2', 'cat-2', 900.0, 0.0),
            # Elena Torres (Max: 1200) -> Verde
            ('ben-5', 'emp-3', 'cat-2', 500.0, 0.0),
            ('ben-6', 'emp-3', 'cat-3', 600.0, 0.0),
            # David Martí (Max: 2000) -> Rojo
            ('ben-7', 'emp-4', 'cat-1', 1000.0, 0.0),
            ('ben-8', 'emp-4', 'cat-5', 900.0, 0.0),
            # Sofía Benítez (Max: 1500) -> Ámbar
            ('ben-9', 'emp-5', 'cat-4', 1000.0, 0.0),
            # Javier López (Max: 2200) -> Verde
            ('ben-10', 'emp-6', 'cat-1', 1000.0, 0.0),
            # Lucía Ramos (Max: 1000) -> Rojo
            ('ben-11', 'emp-7', 'cat-1', 900.0, 0.0),
            # Miguel Ángel Sanz (Max: 800) -> Ámbar
            ('ben-12', 'emp-8', 'cat-6', 700.0, 0.0),
            # Carmen Vega (Max: 1400) -> Verde
            ('ben-13', 'emp-9', 'cat-2', 1200.0, 0.0),
            # Pablo Navarro (Max: 600) -> Rojo
            ('ben-14', 'emp-10', 'cat-1', 550.0, 0.0)
        ]
        cursor.executemany("INSERT INTO benefits VALUES (?, ?, ?, ?, ?)", benefits_data)

        # 5. Generar Gastos (~15 Aprobados, ~6 Pendientes, ~4 Rechazados) (AC-BE-03.5)
        # Diseñados para activar estados Verde (<70%), Ámbar (70-90%) y Rojo (>90%)
        expenses_data = [
            # ben-1 (Comida, Ana Gómez - Allocated: 1000) -> Gasto 600 (Aprobado) -> Verde (60%)
            ('exp-1', 'ben-1', 'Restaurante El Escondite', 'Comida de equipo', 600.0, '2026-03-01', 'Approved'),
            # ben-2 (Formación, Ana Gómez - Allocated: 1200) -> Gasto 1150 (Aprobado) -> Rojo (95.8%)
            ('exp-2', 'ben-2', 'Curso Advanced React', 'Plataforma Udemy Business', 1150.0, '2026-03-05', 'Approved'),
            
            # ben-3 (Comida, Carlos Ruiz - Allocated: 800) -> Gasto 600 (Aprobado) -> Ámbar (75%)
            ('exp-3', 'ben-3', 'Menú diario', 'Comidas mes de marzo', 600.0, '2026-03-02', 'Approved'),
            # ben-4 (Transporte, Carlos Ruiz - Allocated: 900) -> Gasto 200 (Pendiente)
            ('exp-4', 'ben-4', 'Abono Transporte', 'Recarga trimestral', 200.0, '2026-03-10', 'Pending'),
            
            # ben-5 (Transporte, Elena Torres - Allocated: 500) -> Gasto 200 (Aprobado) -> Verde (40%)
            ('exp-5', 'ben-5', 'Metro y Autobús', 'Viajes oficina', 200.0, '2026-03-03', 'Approved'),
            # ben-6 (Guardería, Elena Torres - Allocated: 600) -> Gasto 100 (Rechazado)
            ('exp-6', 'ben-6', 'Escuela Infantil', 'Factura febrero', 100.0, '2026-03-04', 'Rejected'),
            
            # ben-7 (Comida, David Martí - Allocated: 1000) -> Gasto 950 (Aprobado) -> Rojo (95%)
            ('exp-7', 'ben-7', 'Catering clientes', 'Reunión comercial', 950.0, '2026-03-06', 'Approved'),
            # ben-8 (Salud, David Martí - Allocated: 900) -> Gasto 400 (Pendiente)
            ('exp-8', 'ben-8', 'Fisioterapia', 'Tratamiento muscular', 400.0, '2026-03-08', 'Pending'),

            # ben-9 (Formación, Sofía Benítez - Allocated: 1000) -> Gasto 800 (Aprobado) -> Ámbar (80%)
            ('exp-9', 'ben-9', 'Certificación HR', 'SHRM Exam', 800.0, '2026-03-07', 'Approved'),

            # ben-10 (Comida, Javier López - Allocated: 1000) -> Gasto 400 (Aprobado) -> Verde (40%)
            ('exp-10', 'ben-10', 'Comidas de trabajo', 'Almuerzos', 400.0, '2026-03-09', 'Approved'),

            # ben-11 (Comida, Lucía Ramos - Allocated: 900) -> Gasto 850 (Aprobado) -> Rojo (94.4%)
            ('exp-11', 'ben-11', 'Restaurante Centro', 'Comidas de gerencia', 850.0, '2026-03-10', 'Approved'),

            # ben-12 (Gimnasio, Miguel Ángel Sanz - Allocated: 700) -> Gasto 560 (Aprobado) -> Ámbar (80%)
            ('exp-12', 'ben-12', 'Cuota Gimnasio', 'Trimestre GoFit', 560.0, '2026-03-11', 'Approved'),

            # ben-13 (Transporte, Carmen Vega - Allocated: 1200) -> Gasto 500 (Aprobado) -> Verde (41.6%)
            ('exp-13', 'ben-13', 'Parking oficina', 'Abono mensual', 500.0, '2026-03-12', 'Approved'),

            # ben-14 (Comida, Pablo Navarro - Allocated: 550) -> Gasto 520 (Aprobado) -> Rojo (94.5%)
            ('exp-14', 'ben-14', 'Menús diarios', 'Restaurante cercano', 520.0, '2026-03-13', 'Approved'),

            # Gastos adicionales en estado Pendiente (6 en total requeridos)
            ('exp-15', 'ben-1', 'Cena empresa', 'Restaurante La Lonja', 150.0, '2026-03-14', 'Pending'),
            ('exp-16', 'ben-3', 'Parking cliente', 'Visita rápida', 25.0, '2026-03-14', 'Pending'),
            ('exp-17', 'ben-5', 'Taxi urgente', 'Desplazamiento aeropuerto', 45.0, '2026-03-15', 'Pending'),
            ('exp-18', 'ben-9', 'Libro técnico', 'Clean Architecture', 40.0, '2026-03-15', 'Pending'),
            ('exp-19', 'ben-10', 'Cafetería', 'Reunión informal', 30.0, '2026-03-16', 'Pending'),

            # Gastos adicionales en estado Rechazado (4 en total requeridos)
            ('exp-20', 'ben-2', 'Compra material', 'Teclado mecánico', 120.0, '2026-03-01', 'Rejected'),
            ('exp-21', 'ben-7', 'Cena personal', 'Ocio fin de semana', 85.0, '2026-03-02', 'Rejected'),
            ('exp-22', 'ben-11', 'Viaje vacacional', 'Billete tren privado', 300.0, '2026-03-03', 'Rejected'),
            ('exp-23', 'ben-13', 'Multa tráfico', 'Exceso velocidad', 60.0, '2026-03-04', 'Rejected')
        ]
        
        cursor.executemany("INSERT INTO expenses VALUES (?, ?, ?, ?, ?, ?, ?)", expenses_data)

        # 6. Calcular y poblar los acumuladores `spent_amount` basados en gastos 'Approved' (AC-BE-03.6)
        cursor.execute("""
            UPDATE benefits
            SET spent_amount = COALESCE((
                SELECT SUM(amount) 
                FROM expenses 
                WHERE expenses.benefit_id = benefits.id 
                  AND expenses.status = 'Approved'
            ), 0.0);
        """)

        # Confirmar transacción
        conn.commit()
        print("✅ Base de datos poblada exitosamente con datos de prueba.")
        print("📊 Semáforos listos para evaluación (Verde <70%, Ámbar 70-90%, Rojo >90%).")

    except Exception as e:
        conn.rollback()
        print(f"❌ Error durante el seeding de la base de datos: {e}")
        raise e
    finally:
        conn.close()

if __name__ == '__main__':
    seed_database()