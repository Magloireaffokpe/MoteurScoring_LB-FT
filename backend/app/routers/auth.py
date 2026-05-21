from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.config import settings
from app.db.session import get_db
from app.auth.security import verify_password, create_access_token
from app.auth.dependencies import get_current_user
from app.limiter import limiter
from app.models.users import User
from app.schemas.auth import LoginRequest, TokenResponse, UserMe
from app.services.audit_service import log_action

router = APIRouter()


@router.post("/auth/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(data: LoginRequest, response: Response, request: Request, db: Session = Depends(get_db)):
    """
    Connexion sécurisée.
    Message d'erreur générique — ne distingue pas login invalide de mot de passe invalide.
    Token JWT valide 8 heures.
    """
    user = db.query(User).filter(
        User.login == data.login,
        User.is_active
    ).first()

    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Incorrect login or password"
        )

    # Mise à jour dernière connexion
    user.last_login = datetime.now(timezone.utc)
    db.commit()

    token = create_access_token({
        "sub": str(user.id),
        "role": user.role.name
    })

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=not settings.DEBUG,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )

    log_action(db, str(user.id), "LOGIN")

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        role=user.role.name
    )


@router.get("/auth/me", response_model=UserMe)
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "login": current_user.login,
        "role": current_user.role.name,
        "is_active": current_user.is_active,
    }