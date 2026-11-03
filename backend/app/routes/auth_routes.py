"""
/auth endpoints — signup, login, current-user lookup, logout.
"""
from fastapi import APIRouter, Depends, Header

from app import auth as authlib
from app.auth import (
    AuthResponse,
    LoginBody,
    SignupBody,
    UserRecord,
    current_user,
)

router = APIRouter()


@router.post("/register", response_model=AuthResponse, status_code=201)
def register(body: SignupBody):
    return authlib.signup(body)


@router.post("/login", response_model=AuthResponse)
def login(body: LoginBody):
    return authlib.login(body)


@router.get("/me", response_model=UserRecord)
def me(user: UserRecord = Depends(current_user)):
    return user


@router.post("/logout", status_code=204)
def logout(authorization: str | None = Header(default=None)):
    # best-effort — invalidate the presented token if any
    token = authlib._extract_token(authorization)
    if token:
        authlib.logout(token)
    return None
