"""
API endpoints for managing alert recipients.
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Depends
from sqlmodel import select, Session
from pydantic import BaseModel, EmailStr

from api.db import get_session
from api.models import AlertRecipient
from api.security import verify_master_token

router = APIRouter(prefix="/alerts", tags=["alerts"])


class AlertRecipientCreate(BaseModel):
    """Request model for creating an alert recipient."""
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    name: Optional[str] = None
    email_enabled: bool = True
    sms_enabled: bool = True


class AlertRecipientResponse(BaseModel):
    """Response model for alert recipient."""
    id: int
    email: Optional[str]
    phone: Optional[str]
    name: Optional[str]
    email_enabled: bool
    sms_enabled: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


@router.get("/recipients", response_model=List[AlertRecipientResponse])
def list_recipients(
    session: Session = Depends(get_session),
    _: None = Depends(verify_master_token),
):
    """List all alert recipients."""
    recipients = session.exec(select(AlertRecipient)).all()
    return recipients


@router.post("/recipients", response_model=AlertRecipientResponse, status_code=status.HTTP_201_CREATED)
def create_recipient(
    recipient: AlertRecipientCreate,
    session: Session = Depends(get_session),
    _: None = Depends(verify_master_token),
):
    """Create a new alert recipient."""
    if not recipient.email and not recipient.phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either email or phone must be provided"
        )
    
    # Check for duplicates
    if recipient.email:
        existing = session.exec(
            select(AlertRecipient).where(AlertRecipient.email == recipient.email)
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Email {recipient.email} already exists"
            )
    
    if recipient.phone:
        existing = session.exec(
            select(AlertRecipient).where(AlertRecipient.phone == recipient.phone)
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Phone {recipient.phone} already exists"
            )
    
    db_recipient = AlertRecipient(**recipient.model_dump())
    session.add(db_recipient)
    session.commit()
    session.refresh(db_recipient)
    
    return db_recipient


@router.put("/recipients/{recipient_id}", response_model=AlertRecipientResponse)
def update_recipient(
    recipient_id: int,
    recipient: AlertRecipientCreate,
    session: Session = Depends(get_session),
    _: None = Depends(verify_master_token),
):
    """Update an existing alert recipient."""
    db_recipient = session.get(AlertRecipient, recipient_id)
    if not db_recipient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recipient {recipient_id} not found"
        )
    
    # Update fields
    for key, value in recipient.model_dump(exclude_unset=True).items():
        setattr(db_recipient, key, value)
    
    from datetime import datetime
    db_recipient.updated_at = datetime.utcnow()
    
    session.add(db_recipient)
    session.commit()
    session.refresh(db_recipient)
    
    return db_recipient


@router.delete("/recipients/{recipient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recipient(
    recipient_id: int,
    session: Session = Depends(get_session),
    _: None = Depends(verify_master_token),
):
    """Delete an alert recipient."""
    db_recipient = session.get(AlertRecipient, recipient_id)
    if not db_recipient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recipient {recipient_id} not found"
        )
    
    session.delete(db_recipient)
    session.commit()
    
    return None

