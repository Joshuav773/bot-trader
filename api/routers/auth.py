from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from sqlmodel import select

from api.db import get_session
from api.models import User
from api.security import verify_password, create_access_token


router = APIRouter()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/login")
def login(req: LoginRequest, session=Depends(get_session)):
    user = session.exec(select(User).where(User.email == req.email)).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_master:
        raise HTTPException(status_code=403, detail="Access denied")

    token = create_access_token(subject=user.email)
    return {"access_token": token, "token_type": "bearer"}
