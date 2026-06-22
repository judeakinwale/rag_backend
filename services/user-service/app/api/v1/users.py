from fastapi import APIRouter, Depends
from app.core.db import get_db

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/{user_id}")
async def get_user(user_id: int, db=Depends(get_db)):
    return {"id": user_id}


@router.post("")
async def create_user():
    return {"message": "created"}
