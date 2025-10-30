from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr, Field
from sqlmodel import select

from api.db import get_session
from api.models import User
from api.security import hash_password, verify_password, create_access_token


router = APIRouter()


class InitMasterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


@router.post("/init-master")
def init_master(req: InitMasterRequest, session=Depends(get_session)):
    existing_master = session.exec(select(User).where(User.is_master == True)).first()
    if existing_master:
        raise HTTPException(status_code=400, detail="Master already initialized")

    existing_user = session.exec(select(User).where(User.email == req.email)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User with email already exists")

    user = User(email=req.email, password_hash=hash_password(req.password), is_master=True)
    session.add(user)
    session.commit()
    session.refresh(user)
    return {"message": "Master user created", "email": user.email}


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/login")
def login(req: LoginRequest, session=Depends(get_session)):
    user = session.exec(select(User).where(User.email == req.email)).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(subject=user.email)
    return {"access_token": token, "token_type": "bearer"}
