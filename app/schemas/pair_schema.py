from pydantic import BaseModel, EmailStr


class CreateInvitationRequest(BaseModel):
    invited_email: EmailStr | None = None


class AcceptInvitationRequest(BaseModel):
    code: str


class PairStatusResponse(BaseModel):
    has_partner: bool
    couple_id: int | None = None


class InvitationResponse(BaseModel):
    code: str
    inviter_user_id: int
    invited_email: EmailStr | None = None
