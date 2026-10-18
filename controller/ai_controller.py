"""
Pluxee Enterprise - AI Financial Advisor Controller (US-INT-10.3 & US-INT-10.4)

Implements the executive financial advisor flow utilizing Google Genkit Python SDK
and Google Gemini (googleai/gemini-2.0-flash). Analyzes real-time consumption vs caps,
identifies limit threshold alerts (>85%), and generates strategic HR rebalancing recommendations.
Includes a robust local reasoning engine as fallback in case GEMINI_API_KEY is not configured.
"""

from datetime import datetime, timezone
from decimal import Decimal
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from config.config_variables import settings
from model.benefit_model import Benefit
from model.category_model import Category
from model.employee_model import Employee
from model.expense_model import Expense
from schema.ai_schema import (
    AlertBlock,
    BudgetInsightsRequest,
    BudgetInsightsResponse,
    HealthBlock,
    RecommendationBlock,
    StructuredGenkitDiagnosis,
)

logger = logging.getLogger(__name__)

# Global singleton client instance
_genkit_instance = None


def get_genkit_client():
    """
    Lazily initialize and return the Google Genkit client configured with GoogleAI.
    Uses settings.GENKIT_MODEL (default: googleai/gemini-2.0-flash) and GEMINI_API_KEY.
    """
    global _genkit_instance
    if _genkit_instance is not None:
        return _genkit_instance

    api_key = (
        os.getenv("GEMINI_API_KEY")
        or settings.GEMINI_API_KEY
        or os.getenv("GENKIT_API_KEY")
        or settings.GENKIT_API_KEY
    )
    if api_key:
        os.environ["GEMINI_API_KEY"] = api_key

    try:
        from genkit import Genkit
        from genkit_google_genai import GoogleAI

        model_name = settings.GENKIT_MODEL or "googleai/gemini-2.0-flash"
        _genkit_instance = Genkit(plugins=[GoogleAI()], model=model_name)
        logger.info("Google Genkit SDK initialized successfully with model: %s", model_name)
    except Exception as exc:
        logger.warning(
            "Could not initialize Google Genkit SDK (%s). Heuristic fallback will be used when needed.",
            exc,
        )
        _genkit_instance = None

    return _genkit_instance


def is_genkit_available() -> bool:
    """Check if the Google Genkit client and GEMINI_API_KEY are ready for inference."""
    api_key = os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY
    if not api_key:
        return False
    client = get_genkit_client()
    return client is not None


def _format_currency(amount: float, currency: str = "EUR") -> str:
    """Format numeric amount into human-readable currency string."""
    if currency == "MXN":
        return f"${amount:,.2f} MXN"
    return f"€{amount:,.2f}"


def _extract_or_compute_metrics(
    request: Optional[BudgetInsightsRequest], db: Session
) -> Tuple[float, float, float, float, List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Extracts budget metrics from frontend store payload if available,
    or calculates live metrics from the SQLite database models.
    """
    if request and request.metrics and isinstance(request.metrics, dict):
        m = request.metrics
        limit = float(m.get("globalBudgetCap") or m.get("totalLimit") or 45000.0)
        spent = float(m.get("totalSpent") or 0.0)
        available = float(m.get("availableBudget") or max(0.0, limit - spent))
        ratio = float(m.get("spentPercentage") or ((spent / limit * 100.0) if limit > 0 else 0.0))
        categories = list(m.get("categoryBreakdown") or [])
        employees = list(m.get("topConsumingEmployees") or [])
        return limit, spent, available, ratio, categories, employees

    # Query live metrics from database
    total_spent_dec = (
        db.query(func.coalesce(func.sum(Expense.amount), Decimal("0.00")))
        .filter(Expense.status.in_(["PENDING", "APPROVED"]))
        .scalar()
    )
    spent = float(total_spent_dec)

    total_cap_dec = (
        db.query(func.coalesce(func.sum(Employee.max_budget), Decimal("0.00"))).scalar()
    )
    limit = float(total_cap_dec) if float(total_cap_dec) > 0 else 45000.0
    available = max(0.0, limit - spent)
    ratio = round((spent / limit * 100.0), 1) if limit > 0 else 0.0

    # Aggregate categories
    categories = []
    db_cats = db.query(Category).all()
    for cat in db_cats:
        cat_spent_dec = (
            db.query(func.coalesce(func.sum(Expense.amount), Decimal("0.00")))
            .filter(Expense.category_id == cat.id, Expense.status.in_(["PENDING", "APPROVED"]))
            .scalar()
        )
        cat_spent = float(cat_spent_dec)

        cat_assigned_dec = (
            db.query(func.coalesce(func.sum(Benefit.allocated_amount), Decimal("0.00")))
            .filter(Benefit.category_id == cat.id)
            .scalar()
        )
        cat_assigned = float(cat_assigned_dec) if float(cat_assigned_dec) > 0 else (cat_spent * 1.5 or 1000.0)
        cat_pct = round((cat_spent / cat_assigned * 100.0), 1) if cat_assigned > 0 else 0.0

        categories.append({
            "id": cat.id,
            "name": cat.name,
            "spent": cat_spent,
            "assigned": cat_assigned,
            "pct": cat_pct,
            "available": max(0.0, cat_assigned - cat_spent)
        })

    # Aggregate top consuming employees
    employees = []
    db_emps = db.query(Employee).all()
    for emp in db_emps:
        emp_spent_dec = (
            db.query(func.coalesce(func.sum(Expense.amount), Decimal("0.00")))
            .filter(Expense.employee_id == emp.id, Expense.status.in_(["PENDING", "APPROVED"]))
            .scalar()
        )
        emp_spent = float(emp_spent_dec)
        emp_cap = float(emp.max_budget) if float(emp.max_budget) > 0 else 1000.0
        emp_pct = round((emp_spent / emp_cap * 100.0), 1) if emp_cap > 0 else 0.0
        employees.append({
            "id": emp.id,
            "name": f"{emp.first_name} {emp.last_name}",
            "spent": emp_spent,
            "assigned": emp_cap,
            "pct": emp_pct
        })

    employees.sort(key=lambda x: x["pct"], reverse=True)
    return limit, spent, available, ratio, categories, employees


def _build_threshold_alerts(
    categories: List[Dict[str, Any]],
    employees: List[Dict[str, Any]],
    currency: str = "EUR"
) -> Tuple[List[AlertBlock], List[str], List[str]]:
    """Generates alerts for entities nearing or exceeding 85% of budget cap."""
    alerts: List[AlertBlock] = []
    underutilized: List[str] = []
    saturated: List[str] = []

    # Category alerts
    for cat in categories:
        name = cat.get("name", f"Categoría {cat.get('id')}")
        pct = float(cat.get("pct") or 0.0)
        c_spent = float(cat.get("spent") or 0.0)
        c_assigned = float(cat.get("assigned") or 0.0)

        if pct >= 85.0:
            saturated.append(name)
            severity = "critical" if pct >= 95.0 else "warning"
            metric_str = f"{pct:.0f}% ({_format_currency(c_spent, currency)} / {_format_currency(c_assigned, currency)})"
            alerts.append(
                AlertBlock(
                    id=f"alert-cat-{cat.get('id', name)}",
                    type="category",
                    name=name,
                    percentage=pct,
                    metric=metric_str,
                    severity=severity
                )
            )
        elif pct <= 45.0:
            underutilized.append(name)

    # Employee alerts
    for emp in employees:
        name = emp.get("name", f"Empleado {emp.get('id')}")
        pct = float(emp.get("pct") or 0.0)
        e_spent = float(emp.get("spent") or 0.0)
        e_assigned = float(emp.get("assigned") or 0.0)

        if pct >= 85.0:
            severity = "critical" if pct >= 95.0 else "warning"
            metric_str = f"{pct:.0f}% ({_format_currency(e_spent, currency)} / {_format_currency(e_assigned, currency)})"
            alerts.append(
                AlertBlock(
                    id=f"alert-emp-{emp.get('id', name)}",
                    type="employee",
                    name=name,
                    percentage=pct,
                    metric=metric_str,
                    severity=severity
                )
            )

    return alerts, underutilized, saturated


def _generate_local_fallback_diagnosis(
    limit: float,
    spent: float,
    available: float,
    ratio: float,
    alerts: List[AlertBlock],
    underutilized: List[str],
    saturated: List[str],
    currency: str = "EUR"
) -> Tuple[HealthBlock, RecommendationBlock]:
    """
    Deterministic rule-based reasoning engine ensuring 100% operational uptime
    during offline mode or API quota limits (AC-09.3).
    """
    if ratio < 75.0:
        health_status = "optimal"
        status_label = "Óptima"
    elif ratio < 90.0:
        health_status = "warning"
        status_label = "Alerta Preventiva"
    else:
        health_status = "critical"
        status_label = "Límite Crítico"

    spent_str = _format_currency(spent, currency)
    limit_str = _format_currency(limit, currency)
    avail_str = _format_currency(available, currency)

    health_summary = (
        f"Salud Presupuestaria <strong>{status_label}</strong>: Consumo global al <strong>{ratio:.1f}%</strong> "
        f"({spent_str} consumidos de un tope asignado de {limit_str}). Margen disponible de {avail_str}."
    )

    if underutilized and saturated:
        under_str = " y ".join(f"<em>{u}</em>" for u in underutilized)
        sat_str = " y ".join(f"<em>{s}</em>" for s in saturated)
        rec_summary = (
            f"Las categorías {under_str} mantienen más del 45% de remanente disponible. "
            f"Se sugiere transferir un remanente acordado de partida hacia {sat_str} para evitar "
            f"la saturación de los topes antes del cierre de mes."
        )
    elif saturated:
        sat_str = ", ".join(f"<em>{s}</em>" for s in saturated)
        rec_summary = (
            f"Las partidas de {sat_str} muestran una tasa de consumo acelerada (>85%). "
            f"Se recomienda habilitar un incremento temporal en los topes de asignación mediante el botón de edición directa."
        )
    else:
        rec_summary = (
            "La distribución presupuestaria actual es equilibrada y sostenible. "
            "Todos los departamentos y categorías mantienen margen operativo sin requerir reasignación inmediata."
        )

    health = HealthBlock(
        status=health_status,
        spent=spent,
        limit=limit,
        available=available,
        ratio=ratio,
        summaryText=health_summary
    )
    recommendations = RecommendationBlock(
        summaryText=rec_summary,
        underutilized=underutilized,
        saturated=saturated
    )
    return health, recommendations


async def generate_budget_insights(
    request: Optional[BudgetInsightsRequest], db: Session
) -> BudgetInsightsResponse:
    """
    Main controller action: invokes Google Genkit Gemini model or fallback heuristic engine.
    Returns structured 3-part diagnosis contract for Dashboard view (US-INT-10.4).
    """
    currency = request.currency if request and request.currency else "EUR"

    # Step 1: Metric extraction & threshold alert detection
    limit, spent, available, ratio, categories, employees = _extract_or_compute_metrics(
        request, db
    )
    alerts, underutilized, saturated = _build_threshold_alerts(
        categories, employees, currency
    )

    now_iso = datetime.now(timezone.utc).isoformat()
    ai_client = get_genkit_client()

    # Step 2: Attempt Genkit Gemini Structured Generation if client initialized and key available
    api_key = os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY
    if ai_client is not None and api_key:
        try:
            prompt = (
                "Actúa como un asesor financiero senior de Recursos Humanos para la plataforma empresarial Pluxee.\n"
                "Analiza la siguiente situación financiera corporativa en tiempo real:\n"
                f"- Presupuesto Total / Tope Global: {_format_currency(limit, currency)}\n"
                f"- Consumo Ejecutado: {_format_currency(spent, currency)} ({ratio:.1f}% del tope asignado)\n"
                f"- Saldo Remanente Disponible: {_format_currency(available, currency)}\n"
                f"- Categorías saturadas (>85% consumo): {', '.join(saturated) if saturated else 'Ninguna'}\n"
                f"- Categorías infrautilizadas (<45% consumo): {', '.join(underutilized) if underutilized else 'Ninguna'}\n"
                f"- Cantidad de alertas activas: {len(alerts)}\n\n"
                "Genera un diagnóstico financiero estructurado en español profesional, directo y ejecutivo:\n"
                "1. health_status: 'optimal' si ratio < 75%, 'warning' si 75% <= ratio < 90%, 'critical' si ratio >= 90%.\n"
                "2. health_summary: Un párrafo conciso evaluando la salud presupuestaria para el cuadro de mandos de RRHH.\n"
                "3. recommendation_summary: Recomendación estratégica de rebalanceo entre partidas infrautilizadas y saturadas o ajuste de topes.\n"
                "4. underutilized_categories: lista de nombres de categorías con bajo consumo.\n"
                "5. saturated_categories: lista de nombres de categorías al borde del tope.\n"
            )

            res = await ai_client.generate(
                prompt=prompt,
                output_format="json",
                output_schema=StructuredGenkitDiagnosis,
            )

            diag: StructuredGenkitDiagnosis = res.output
            if diag:
                health = HealthBlock(
                    status=diag.health_status or ("optimal" if ratio < 75 else "warning" if ratio < 90 else "critical"),
                    spent=spent,
                    limit=limit,
                    available=available,
                    ratio=ratio,
                    summaryText=diag.health_summary or f"Consumo global al {ratio:.1f}% con margen de {_format_currency(available, currency)}."
                )
                recs = RecommendationBlock(
                    summaryText=diag.recommendation_summary,
                    underutilized=diag.underutilized_categories or underutilized,
                    saturated=diag.saturated_categories or saturated
                )
                return BudgetInsightsResponse(
                    success=True,
                    source="google-genkit-advisor-v1",
                    timestamp=now_iso,
                    health=health,
                    alerts=alerts,
                    recommendations=recs
                )
        except Exception as exc:
            logger.warning(
                "Genkit LLM generation encountered an error (%s). Falling back to heuristic reasoning engine.",
                exc,
            )

    # Step 3: Heuristic fallback (guarantees 100% availability with 0 crashes)
    health, recommendations = _generate_local_fallback_diagnosis(
        limit, spent, available, ratio, alerts, underutilized, saturated, currency
    )
    return BudgetInsightsResponse(
        success=True,
        source="google-genkit-advisor-fallback",
        timestamp=now_iso,
        health=health,
        alerts=alerts,
        recommendations=recommendations,
    )
