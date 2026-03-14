from datetime import datetime
import secrets
from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.deps import get_db
from app.models.couple import Couple
from app.models.invitation import Invitation
from app.models.user import User
from app.schemas.pair_schema import (
    AcceptInvitationRequest,
    CreateInvitationRequest,
    InvitationResponse,
    PairStatusResponse,
)
from app.security.auth import get_current_user

router = APIRouter()


def _generate_invitation_code() -> str:
    return secrets.token_urlsafe(8).upper()


@router.get("/pair/status", response_model=PairStatusResponse)
def pair_status(current_user: User = Depends(get_current_user)):
    couple_id = cast(int | None, cast(Any, current_user.couple_id))
    has_partner = couple_id is not None
    return PairStatusResponse(has_partner=has_partner, couple_id=couple_id)


@router.post("/pair/invite", response_model=InvitationResponse)
def create_invitation(
    payload: CreateInvitationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.couple_id is not None:
        raise HTTPException(status_code=400, detail="Ya estas vinculado a una pareja")

    for _ in range(5):
        code = _generate_invitation_code()
        exists = db.query(Invitation).filter(Invitation.code == code).first()
        if not exists:
            invitation = Invitation(
                code=code,
                inviter_user_id=current_user.id,
                invited_email=payload.invited_email,
                accepted=False,
            )
            db.add(invitation)
            db.commit()
            db.refresh(invitation)
            return InvitationResponse(
                code=str(cast(Any, invitation.code)),
                inviter_user_id=int(cast(Any, invitation.inviter_user_id)),
                invited_email=cast(str | None, cast(Any, invitation.invited_email)),
            )

    raise HTTPException(status_code=500, detail="No se pudo generar codigo de invitacion")


@router.post("/pair/accept", response_model=PairStatusResponse)
def accept_invitation(
    payload: AcceptInvitationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.couple_id is not None:
        raise HTTPException(status_code=400, detail="Ya estas vinculado a una pareja")

    invitation = db.query(Invitation).filter(Invitation.code == payload.code.strip().upper()).first()

    if not invitation:
        raise HTTPException(status_code=404, detail="Codigo de invitacion no valido")

    if bool(cast(Any, invitation.accepted)):
        raise HTTPException(status_code=400, detail="La invitacion ya fue aceptada")

    inviter = db.query(User).filter(User.id == invitation.inviter_user_id).first()
    if not inviter:
        raise HTTPException(status_code=404, detail="Invitador no encontrado")

    if int(cast(Any, inviter.id)) == int(cast(Any, current_user.id)):
        raise HTTPException(status_code=400, detail="No puedes aceptar tu propia invitacion")

    if inviter.couple_id is not None:
        couple_id = inviter.couple_id
    else:
        couple = Couple()
        db.add(couple)
        db.flush()
        couple_id = couple.id
        setattr(inviter, "couple_id", couple_id)

    setattr(current_user, "couple_id", couple_id)
    setattr(invitation, "accepted", True)
    setattr(invitation, "accepted_at", datetime.utcnow())

    db.commit()

    return PairStatusResponse(has_partner=True, couple_id=int(cast(Any, couple_id)))
