#Dépendances FastAPI pour récupérer l'utilisateur courant depuis le token.

from typing import Optional
from fastapi import Depends, HTTPException, Cookie
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.auth.security import decode_token
from app.db.session import get_db
from app.models.users import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    access_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
) -> User:
    actual_token = access_token or token
    if not actual_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = decode_token(actual_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = db.query(User).filter(
        User.id == payload.get("sub"),
        User.is_active == True
    ).first()

    if not user:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role.name != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return current_user


def require_compliance_or_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role.name not in ["admin", "compliance_officer"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return current_user