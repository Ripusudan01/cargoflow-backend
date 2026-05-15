from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .rag_pipeline import CargoFlowRAG

router = APIRouter()

rag: Optional[CargoFlowRAG] = None


@asynccontextmanager
async def lifespan(app):
    global rag
    print("[chatbot] Loading RAG pipeline...")
    rag = CargoFlowRAG()
    print("[chatbot] Ready.")
    yield


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

    if rag is None:
        raise HTTPException(503, "Chatbot not initialized")

    result = rag.query(request.question.strip(), top_k=request.top_k)

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
async def rebuild():

    if rag is None:
        raise HTTPException(503, "Chatbot not initialized")

    rag.rebuild()

    return {
        "message": "Rebuilt successfully",
        "chunks_loaded": len(rag.chunks),
    }