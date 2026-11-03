from fastapi import APIRouter, Depends

from app import classroom as cls
from app.auth import UserRecord, current_user

router = APIRouter()


@router.get("")
def list_notifications(user: UserRecord = Depends(current_user)):
    notes = cls.get_notifications(user.id)
    return [n.model_dump() for n in notes]


@router.get("/unread-count")
def unread_count(user: UserRecord = Depends(current_user)):
    notes = cls.get_notifications(user.id)
    return {"count": sum(1 for n in notes if not n.read)}


@router.post("/mark-read")
def mark_read(user: UserRecord = Depends(current_user)):
    count = cls.mark_notifications_read(user.id)
    return {"marked": count}
