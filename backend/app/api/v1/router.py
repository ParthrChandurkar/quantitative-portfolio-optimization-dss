from fastapi import APIRouter

from app.api.v1 import (
    analytics,
    auth,
    me,
    optimization,
    portfolios,
    reports,
    scenarios,
    stocks,
)

api_router = APIRouter(prefix="/api/v1")
for router in (
    auth.router,
    me.router,
    stocks.router,
    portfolios.router,
    optimization.router,
    scenarios.router,
    analytics.router,
    reports.router,
):
    api_router.include_router(router)
