"""
Auth routes. POC: plain email/password + JWT. Signup always creates a new
org with the signing-up user as 'owner' — inviting additional members to
an existing org is a natural next endpoint (not needed for the POC flow).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Organization, Membership
from app.schemas.auth import SignupRequest, LoginRequest, TokenResponse
from app.core.security import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


def _slugify(name: str) -> str:
    return "-".join(name.lower().split())[:50]


@router.post("/signup", response_model=TokenResponse)
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    user = User(email=payload.email, hashed_password=hash_password(payload.password),
                display_name=payload.display_name)
    db.add(user)
    db.flush()

    org = Organization(name=payload.organization_name, slug=_slugify(payload.organization_name))
    db.add(org)
    db.flush()

    db.add(Membership(user_id=user.id, organization_id=org.id, role="owner"))
    db.commit()

    token = create_access_token(user_id=user.id, organization_id=org.id)
    return TokenResponse(access_token=token, organization_id=org.id, user_id=user.id)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

    membership = db.query(Membership).filter(Membership.user_id == user.id).first()
    if not membership:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "User has no organization membership")

    token = create_access_token(user_id=user.id, organization_id=membership.organization_id)
    return TokenResponse(access_token=token, organization_id=membership.organization_id, user_id=user.id)
