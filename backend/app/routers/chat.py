from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.security import get_current_user
from app.config import get_settings
from app.database.session import get_db
from app.models import User
from app.schemas import ChatRequest, ChatResponse, ChatStatusResponse
from app.services.chat_service import _can_access_company, chat_reply

router = APIRouter(prefix="/chat", tags=["chat"])
settings = get_settings()


@router.get("/status", response_model=ChatStatusResponse)
def chat_status(current_user: User = Depends(get_current_user)):
    return ChatStatusResponse(
        enabled=bool(settings.openai_api_key),
        model=settings.openai_model if settings.openai_api_key else None,
    )


@router.post("/", response_model=ChatResponse)
def send_message(
    data: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not data.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    if data.company_id is not None and not _can_access_company(current_user, data.company_id):
        raise HTTPException(status_code=403, detail="Insufficient permissions for this company")

    history = [{"role": m.role, "content": m.content} for m in data.history]
    reply = chat_reply(
        db,
        current_user,
        data.message.strip(),
        company_id=data.company_id,
        history=history,
    )
    return ChatResponse(reply=reply)
