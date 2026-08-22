from fastapi import APIRouter

from app.api.v1 import (
    alerts,
    analytics,
    assistant,
    auth,
    me,
    optimization,
    personalization,
    portfolios,
    reports,
    scenarios,
    stocks,
)

api_router = APIRouter(prefix="/api/v1")
for router in (
    auth.router,
    me.router,
    personalization.router,
    stocks.router,
    portfolios.router,
    optimization.router,
    scenarios.router,
    analytics.router,
    alerts.router,
    assistant.router,
    reports.router,
):
    api_router.include_router(router)
