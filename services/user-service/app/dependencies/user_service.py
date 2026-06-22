from fastapi import Depends
from app import container
from app.core.db import get_db


def get_user_service(db=Depends(get_db)):
    return container.user_service(db)
