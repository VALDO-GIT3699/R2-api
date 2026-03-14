from datetime import datetime, timedelta, timezone
from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.deps import get_db
from app.models.appointment import Appointment
from app.models.user import User
from app.schemas.appointment_schema import (
    AppointmentCreateRequest,
    AppointmentReminderResponse,
    AppointmentResponse,
)
from app.security.auth import get_current_user

router = APIRouter()


def _require_partner(current_user: User) -> int:
    couple_id = cast(int | None, cast(Any, current_user.couple_id))
    if couple_id is None:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "PAIR_REQUIRED",
                "message": "Debes vincularte con tu pareja antes de gestionar citas.",
            },
        )
    return couple_id


@router.post("/appointments", response_model=AppointmentResponse)
def create_appointment(
    payload: AppointmentCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    couple_id = _require_partner(current_user)

    scheduled_for = payload.scheduled_for
    if scheduled_for.tzinfo is not None:
        scheduled_for = scheduled_for.astimezone(timezone.utc).replace(tzinfo=None)

    if scheduled_for <= datetime.utcnow():
        raise HTTPException(status_code=400, detail="La cita debe ser futura")

    appointment = Appointment(
        couple_id=couple_id,
        creator_user_id=int(cast(Any, current_user.id)),
        title=payload.title.strip(),
        notes=(payload.notes or "").strip() or None,
        scheduled_for=scheduled_for,
    )

    db.add(appointment)
    db.commit()
    db.refresh(appointment)

    return AppointmentResponse(
        id=int(cast(Any, appointment.id)),
        couple_id=int(cast(Any, appointment.couple_id)),
        creator_user_id=int(cast(Any, appointment.creator_user_id)),
        title=str(cast(Any, appointment.title)),
        notes=cast(str | None, cast(Any, appointment.notes)),
        scheduled_for=cast(datetime, cast(Any, appointment.scheduled_for)),
        created_at=cast(datetime, cast(Any, appointment.created_at)),
    )


@router.get("/appointments", response_model=list[AppointmentResponse])
def list_appointments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    couple_id = _require_partner(current_user)

    appointments = (
        db.query(Appointment)
        .filter(Appointment.couple_id == couple_id)
        .order_by(Appointment.scheduled_for.asc())
        .all()
    )

    return [
        AppointmentResponse(
            id=int(cast(Any, item.id)),
            couple_id=int(cast(Any, item.couple_id)),
            creator_user_id=int(cast(Any, item.creator_user_id)),
            title=str(cast(Any, item.title)),
            notes=cast(str | None, cast(Any, item.notes)),
            scheduled_for=cast(datetime, cast(Any, item.scheduled_for)),
            created_at=cast(datetime, cast(Any, item.created_at)),
        )
        for item in appointments
    ]


@router.get("/appointments/reminders/upcoming", response_model=list[AppointmentReminderResponse])
def upcoming_reminders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    couple_id = _require_partner(current_user)

    now = datetime.utcnow()
    week_window_end = now + timedelta(days=7, hours=1)
    day_window_end = now + timedelta(days=1, hours=1)

    appointments = (
        db.query(Appointment)
        .filter(Appointment.couple_id == couple_id)
        .filter(Appointment.scheduled_for > now)
        .all()
    )

    reminders: list[AppointmentReminderResponse] = []
    for item in appointments:
        scheduled_for = cast(datetime, cast(Any, item.scheduled_for))

        week_trigger = scheduled_for - timedelta(days=7)
        day_trigger = scheduled_for - timedelta(days=1)

        if now <= week_trigger <= week_window_end:
            reminders.append(
                AppointmentReminderResponse(
                    id=int(cast(Any, item.id)),
                    title=str(cast(Any, item.title)),
                    notes=cast(str | None, cast(Any, item.notes)),
                    scheduled_for=scheduled_for,
                    days_until=7,
                )
            )

        if now <= day_trigger <= day_window_end:
            reminders.append(
                AppointmentReminderResponse(
                    id=int(cast(Any, item.id)),
                    title=str(cast(Any, item.title)),
                    notes=cast(str | None, cast(Any, item.notes)),
                    scheduled_for=scheduled_for,
                    days_until=1,
                )
            )

    reminders.sort(key=lambda item: item.scheduled_for)
    return reminders
