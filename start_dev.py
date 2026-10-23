#!/usr/bin/env python3
"""
Pluxee Enterprise HR Suite - Unified Local Development Server
Starts both the FastAPI Backend and the Vanilla JS Frontend,
ensures database tables and seed fixtures are ready,
and opens the application in your default browser.

Usage:
    python start_dev.py
    python start_dev.py --seed
    python start_dev.py --no-browser
    python start_dev.py --backend-port 8000 --frontend-port 5500
"""

import argparse
import os
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

# Configure Windows console encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Paths definition
BACKEND_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = (BACKEND_DIR.parent / "pluxee-frontend").resolve()

# Auto-detect virtual environment python
VENV_PYTHON = BACKEND_DIR / ".venv" / "Scripts" / "python.exe"
if not VENV_PYTHON.exists():
    VENV_PYTHON = BACKEND_DIR / ".venv" / "bin" / "python"
PYTHON_EXE = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a network port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def find_available_port(start_port: int, max_attempts: int = 10, host: str = "127.0.0.1") -> int:
    """Find the next available port starting from start_port."""
    for port in range(start_port, start_port + max_attempts):
        if not is_port_in_use(port, host):
            return port
    return start_port


def wait_for_port(port: int, timeout: float = 8.0, host: str = "127.0.0.1") -> bool:
    """Wait until a local port is listening."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if is_port_in_use(port, host):
            return True
        time.sleep(0.2)
    return False


def check_and_seed_database(python_exe: str, backend_dir: Path, force_seed: bool = False) -> bool:
    """
    Check if database tables and fixtures are present.
    If tables or data are missing (or force_seed is True), execute database/seed.py.
    """
    if force_seed:
        print("\n[*] Se solicitó forzar el reseteo de la base de datos (--seed / --reset-db).")
        print("[*] Ejecutando database/seed.py...")
        res = subprocess.run([python_exe, "database/seed.py"], cwd=str(backend_dir))
        return res.returncode == 0

    print("\n[*] Verificando estado de la base de datos...")
    check_code = (
        "import sys\n"
        "from sqlalchemy import inspect\n"
        "from database.database import engine, SessionLocal\n"
        "from model.company_model import Company\n"
        "from model.category_model import Category\n"
        "from model.employee_model import Employee\n"
        "\n"
        "try:\n"
        "    inspector = inspect(engine)\n"
        "    tables = set(inspector.get_table_names())\n"
        "    required = {'company', 'categories', 'employees', 'benefits', 'expenses'}\n"
        "    if not required.issubset(tables):\n"
        "        print('MISSING_TABLES')\n"
        "        sys.exit(0)\n"
        "    with SessionLocal() as db:\n"
        "        has_data = (\n"
        "            db.query(Company).first() is not None and\n"
        "            db.query(Category).first() is not None and\n"
        "            db.query(Employee).first() is not None\n"
        "        )\n"
        "        if not has_data:\n"
        "            print('EMPTY_DATA')\n"
        "            sys.exit(0)\n"
        "    print('DB_OK')\n"
        "except Exception as e:\n"
        "    print(f'CHECK_ERROR: {e}')\n"
        "    sys.exit(0)\n"
    )

    result = subprocess.run(
        [python_exe, "-c", check_code],
        cwd=str(backend_dir),
        capture_output=True,
        text=True,
    )
    status = result.stdout.strip()

    if status == "DB_OK":
        print("   \033[1;32m[OK] Base de datos verificada: tablas y fixtures existentes.\033[0m")
        return True

    reason = (
        "tablas no encontradas"
        if "MISSING_TABLES" in status
        else ("tablas vacías sin datos" if "EMPTY_DATA" in status else f"estado: {status}")
    )
    print(f"   \033[1;33m[*] Base de datos requiere inicialización ({reason}).\033[0m")
    print("   [*] Ejecutando database/seed.py para crear tablas y fixtures...")
    seed_result = subprocess.run(
        [python_exe, "database/seed.py"],
        cwd=str(backend_dir),
    )
    if seed_result.returncode != 0:
        print("   \033[1;31m[!] Error durante la ejecución de seed.py.\033[0m")
        return False

    print("   \033[1;32m[OK] Base de datos creada y poblada exitosamente.\033[0m")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Launch Pluxee Backend & Frontend servers for integrated local testing."
    )
    parser.add_argument(
        "--backend-port",
        type=int,
        default=8000,
        help="Port for FastAPI backend (default: 8000)",
    )
    parser.add_argument(
        "--frontend-port",
        type=int,
        default=5500,
        help="Port for Frontend static server (default: 5500)",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not open browser automatically upon startup",
    )
    parser.add_argument(
        "--seed",
        "--reset-db",
        dest="force_seed",
        action="store_true",
        help="Force database re-creation and fixture seeding before launch",
    )
    args = parser.parse_args()

    print("=" * 68)
    print("   \033[1;36mPLUXEE ENTERPRISE HR SUITE - LOCAL DEVELOPMENT SERVER\033[0m")
    print("=" * 68)
    print(f"[*] Python Interpreter : {PYTHON_EXE}")
    print(f"[*] Backend Directory  : {BACKEND_DIR}")
    print(f"[*] Frontend Directory : {FRONTEND_DIR}")

    if not FRONTEND_DIR.exists():
        print(f"[!] Warning: Frontend folder not found at {FRONTEND_DIR}")

    # Ensure database is initialized and seeded before booting servers
    if not check_and_seed_database(PYTHON_EXE, BACKEND_DIR, force_seed=args.force_seed):
        print("\n[!] Falló la inicialización de la base de datos. Abortando inicio.")
        sys.exit(1)

    backend_port = args.backend_port
    if is_port_in_use(backend_port):
        print(f"[!] Warning: Port {backend_port} is already active.")
        alt_backend = find_available_port(backend_port + 1)
        print(f"    Will attempt port {alt_backend} for the backend.")
        backend_port = alt_backend

    frontend_port = args.frontend_port
    if is_port_in_use(frontend_port):
        print(f"[*] Notice: Port {frontend_port} is already in use (e.g., VS Code Live Server).")
        alt_frontend = find_available_port(frontend_port + 1)
        print(f"    Starting internal static server on port {alt_frontend}...")
        frontend_port = alt_frontend

    processes = []

    try:
        # 1. Start FastAPI Backend
        print(f"\n[+] Starting FastAPI backend on http://127.0.0.1:{backend_port}...")
        backend_cmd = [
            PYTHON_EXE,
            "-m",
            "uvicorn",
            "main:app",
            "--reload",
            "--port",
            str(backend_port),
            "--host",
            "127.0.0.1",
        ]
        backend_proc = subprocess.Popen(backend_cmd, cwd=str(BACKEND_DIR))
        processes.append(("Backend (FastAPI)", backend_proc))

        # 2. Start Frontend Static Server (if folder exists)
        if FRONTEND_DIR.exists():
            print(f"[+] Starting Frontend static server on http://127.0.0.1:{frontend_port}...")
            frontend_cmd = [
                PYTHON_EXE,
                "-m",
                "http.server",
                str(frontend_port),
                "--directory",
                str(FRONTEND_DIR),
                "--bind",
                "127.0.0.1",
            ]
            frontend_proc = subprocess.Popen(frontend_cmd, cwd=str(FRONTEND_DIR))
            processes.append(("Frontend (HTTP)", frontend_proc))

        # 3. Wait for readiness
        print("[*] Waiting for services to initialize...")
        wait_for_port(backend_port, timeout=6.0)
        if FRONTEND_DIR.exists():
            wait_for_port(frontend_port, timeout=6.0)

        frontend_url = f"http://127.0.0.1:{frontend_port}/"
        docs_url = f"http://127.0.0.1:{backend_port}/docs"

        print("\n" + "=" * 68)
        print("   \033[1;32mALL SERVICES ARE UP AND RUNNING!\033[0m")
        print("=" * 68)
        print(f"   Frontend App        : \033[1;34m{frontend_url}\033[0m")
        print(f"   Dashboard View      : \033[1;34m{frontend_url}#dashboard\033[0m")
        print(f"   Backend Swagger API : \033[1;34m{docs_url}\033[0m")
        print("=" * 68)
        print("   \033[1;33mPress CTRL+C anytime to stop all servers simultaneously.\033[0m")
        print("=" * 68 + "\n")

        # 4. Open default browser
        #if not args.no_browser and FRONTEND_DIR.exists():
        #    time.sleep(0.6)
        #    webbrowser.open(frontend_url)

        # 5. Monitor processes loop
        while True:
            for name, proc in processes:
                status = proc.poll()
                if status is not None:
                    print(f"[!] {name} stopped unexpectedly (exit code {status}).")
                    return
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n\n[*] Received interrupt signal (CTRL+C). Shutting down servers...")
    finally:
        for name, proc in processes:
            if proc.poll() is None:
                print(f"[*] Stopping {name} (PID: {proc.pid})...")
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
        print("[*] All processes stopped cleanly. Goodbye!\n")


if __name__ == "__main__":
    main()
