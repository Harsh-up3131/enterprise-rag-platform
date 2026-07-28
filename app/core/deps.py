"""
Auth/tenancy dependencies shared by every route.

Every authenticated route resolves (user, organization, role) from the JWT
here — routes and services never take `organization_id` as a bare request
parameter. This is what makes "authorization occurs before model exposure"
(blueprint §4.3) enforceable: the tenant/user context is established once,
centrally, before any service code runs.
"""
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.database import get_db
from app.models import User, Membership

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


@dataclass
class RequestContext:
    """Everything downstream services need to know about 'who is asking'."""
    user: User
    organization_id: str
    role: str


def get_current_context(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> RequestContext:
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")

    user = db.get(User, payload["sub"])
    if not user or user.status != "active":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found or inactive")

    organization_id = payload["org"]
    membership = (
        db.query(Membership)
        .filter(Membership.user_id == user.id, Membership.organization_id == organization_id)
        .first()
    )
    if not membership or membership.status != "active":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No active membership in this organization")

    return RequestContext(user=user, organization_id=organization_id, role=membership.role)


def require_role(*allowed_roles: str):
    """Route dependency factory: `Depends(require_role('owner', 'admin'))`."""
    def _check(ctx: RequestContext = Depends(get_current_context)) -> RequestContext:
        if ctx.role not in allowed_roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Requires one of roles: {allowed_roles}")
        return ctx
    return _check
