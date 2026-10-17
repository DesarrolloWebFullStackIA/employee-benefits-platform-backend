from fastapi import APIRouter
from routes.ai_routes import router as ai_router
from routes.category_routes import router as category_router
from routes.dashboard_routes import router as dashboard_router
from routes.employee_routes import router as employee_router
from routes.expense_routes import router as expense_router
from routes.upload_routes import router as upload_router

api_router = APIRouter(prefix="/api/v1")

# Mount sub-routers
api_router.include_router(employee_router)
api_router.include_router(expense_router)
api_router.include_router(category_router)
api_router.include_router(dashboard_router)
api_router.include_router(upload_router)
api_router.include_router(ai_router)


@api_router.get("/status", tags=["System"])
def api_status():
    """Returns the operational status of the API v1."""
    return {
        "success": True,
        "message": "Pluxee Enterprise HR Suite API v1 is operational",
    }
