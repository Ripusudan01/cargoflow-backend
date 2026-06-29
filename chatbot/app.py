import asyncio
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import require_role
from app.models import User, UserRole

from .rag_pipeline import CargoFlowRAG

router = APIRouter()

rag: Optional[CargoFlowRAG] = None
rag_lock = asyncio.Lock()


async def get_rag() -> CargoFlowRAG:
    global rag

    if rag is not None:
        return rag

    async with rag_lock:
        if rag is None:
            rag = await asyncio.to_thread(CargoFlowRAG)

    return rag


# ── Schemas ─────────────────────────

class ChatRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=500)
    top_k: int = Field(default=5, ge=1, le=10)


class SourceChunk(BaseModel):
    text: str
    score: float


class ChatResponse(BaseModel):
    question: str
    answer: str
    found_in_kb: bool
    sources: List[SourceChunk]


# ── Endpoints ───────────────────────

@router.post("/chat", response_model=ChatResponse, tags=["Chatbot"])
async def chat(request: ChatRequest):

    current_rag = await get_rag()

    result = await asyncio.to_thread(
        current_rag.query,
        request.question.strip(),
        top_k=request.top_k
    )

    return ChatResponse(
        question=result["question"],
        answer=result["answer"],
        found_in_kb=result["found_in_kb"],
        sources=[
            SourceChunk(text=text, score=round(score, 4))
            for text, score in result["sources"]
        ],
    )


@router.post("/rebuild", tags=["Chatbot"])
async def rebuild(current_user: User = Depends(require_role(UserRole.ADMIN))):

    current_rag = await get_rag()

    await asyncio.to_thread(current_rag.rebuild)

    return {
        "message": "Rebuilt successfully",
        "chunks_loaded": len(current_rag.chunks),
    }
