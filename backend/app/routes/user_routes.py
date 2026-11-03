"""
Minimal in-memory user registry — stand-in for real auth. Just enough so
the teacher dashboard can list students without forging a login flow.
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, List

from app.models.user import User

router = APIRouter()

_users: Dict[str, User] = {}


@router.get("", response_model=List[User])
def list_users():
    return list(_users.values())


@router.post("", response_model=User, status_code=201)
def upsert_user(user: User):
    _users[user.id] = user
    return user


@router.get("/{user_id}", response_model=User)
def get_user(user_id: str):
    u = _users.get(user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return u
