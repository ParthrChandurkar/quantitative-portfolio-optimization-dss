from __future__ import annotations

import uuid

from fastapi import APIRouter
from sqlalchemy import select

from app.alerts.service import check_alerts
from app.core.deps import CurrentUser, DBSession
from app.core.errors import APIError
from app.db.models import Alert
from app.schemas.alerts import AlertResponse
from app.schemas.common import success
from app.services.portfolio_service import require_owned_portfolio

router = APIRouter(tags=["alerts"])


def _payload(alert: Alert) -> dict:
    return AlertResponse.model_validate(alert, from_attributes=True).model_dump()


@router.get("/me/alerts")
async def list_my_alerts(session: DBSession, user: CurrentUser) -> dict:
    alerts = (
        await session.scalars(
            select(Alert)
            .where(Alert.user_id == user.id)
            .order_by(Alert.created_at.desc(), Alert.id.desc())
        )
    ).all()
    return success([_payload(alert) for alert in alerts])


@router.patch("/me/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: uuid.UUID, session: DBSession, user: CurrentUser
) -> dict:
    alert = await session.scalar(
        select(Alert).where(Alert.id == alert_id, Alert.user_id == user.id)
    )
    if alert is None:
        raise APIError(403, "ALERT_FORBIDDEN", "You do not own this alert")
    alert.acknowledged = True
    await session.commit()
    await session.refresh(alert)
    return success(_payload(alert))


@router.post("/portfolios/{portfolio_id}/alerts/check")
async def check_portfolio_alerts(
    portfolio_id: uuid.UUID, session: DBSession, user: CurrentUser
) -> dict:
    await require_owned_portfolio(session, portfolio_id, user.id)
    alerts = await check_alerts(session, user.id, portfolio_id)
    return success([_payload(alert) for alert in alerts])
