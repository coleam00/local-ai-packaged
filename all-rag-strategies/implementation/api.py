"""
FastAPI service wrapper for the RAG Agent.
Provides HTTP endpoints for the n8n and Open WebUI integrations.
"""

import os
import asyncio
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables (from project root or here)
load_dotenv(".env")
load_dotenv(os.path.join(os.getcwd(), ".env"))

# Import RAG agent components (available within implementation package)
from rag_agent_advanced import (
    agent,
    initialize_db,
    close_db,
    search_knowledge_base,
    search_with_multi_query,
    search_with_reranking,
    search_with_self_reflection,
    retrieve_full_document,
)

# Optional: DB health check uses the same db_pool used by the agent
from utils.db_utils import db_pool

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Initializing RAG service...")
    await initialize_db()
    print("✓ RAG service initialized")
    yield
    # Shutdown
    print("Shutting down RAG service...")
    await close_db()
    print("✓ RAG service shut down")

app = FastAPI(
    title="RAG Agent API",
    description="Advanced RAG system with multiple retrieval strategies",
    version="1.0.0",
    lifespan=lifespan,
)

class ChatRequest(BaseModel):
    message: str = Field(..., description="User message/query")
    session_id: Optional[str] = Field(default="default", description="Session ID for conversation history")
    strategy: Optional[str] = Field(default="auto", description="RAG strategy: auto, standard, multi-query, reranking, self-reflection")
    stream: bool = Field(default=False, description="Stream response")

class ChatResponse(BaseModel):
    response: str
    session_id: str
    sources: List[dict] = []
    metadata: dict = {}

class SearchRequest(BaseModel):
    query: str
    limit: int = Field(default=5, ge=1, le=20)
    strategy: str = Field(default="standard", description="Search strategy")

class SearchResponse(BaseModel):
    results: List[dict]
    query: str
    strategy: str

class HealthResponse(BaseModel):
    status: str
    database: str
    agent: str

conversation_histories: dict[str, list] = {}

@app.get("/health", response_model=HealthResponse)
async def health_check():
    try:
        async with db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return HealthResponse(
        status="healthy" if db_status == "healthy" else "degraded",
        database=db_status,
        agent="healthy",
    )

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        if request.session_id not in conversation_histories:
            conversation_histories[request.session_id] = []
        message_history = conversation_histories[request.session_id]
        result = await agent.run(request.message, message_history=message_history)
        conversation_histories[request.session_id] = result.all_messages()
        response_text = result.data if hasattr(result, "data") else str(result)
        return ChatResponse(
            response=response_text,
            session_id=request.session_id,
            sources=[],
            metadata={"strategy": request.strategy},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")

@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    async def generate():
        try:
            if request.session_id not in conversation_histories:
                conversation_histories[request.session_id] = []
            message_history = conversation_histories[request.session_id]
            async with agent.run_stream(request.message, message_history=message_history) as result:
                async for text in result.stream_text(delta=True):
                    yield f"data: {text}\n\n"
                conversation_histories[request.session_id] = result.all_messages()
                yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: Error: {str(e)}\n\n"

    from fastapi.responses import StreamingResponse
    return StreamingResponse(generate(), media_type="text/event-stream")

@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    try:
        if request.strategy == "multi-query":
            results_text = await search_with_multi_query(None, request.query, request.limit)
        elif request.strategy == "reranking":
            results_text = await search_with_reranking(None, request.query, request.limit)
        elif request.strategy == "self-reflection":
            results_text = await search_with_self_reflection(None, request.query, request.limit)
        else:
            results_text = await search_knowledge_base(None, request.query, request.limit)
        return SearchResponse(results=[{"content": results_text}], query=request.query, strategy=request.strategy)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.get("/documents")
async def list_documents():
    try:
        async with db_pool.acquire() as conn:
            docs = await conn.fetch(
                """
                SELECT 
                    id::text,
                    title,
                    source,
                    created_at,
                    (SELECT COUNT(*) FROM chunks WHERE document_id = documents.id) as chunk_count
                FROM documents
                ORDER BY created_at DESC
                """
            )
        return [
            {
                "id": doc["id"],
                "title": doc["title"],
                "source": doc["source"],
                "created_at": doc["created_at"].isoformat(),
                "chunk_count": doc["chunk_count"],
            }
            for doc in docs
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")

@app.get("/documents/{document_id}")
async def get_document(document_id: str):
    try:
        result = await retrieve_full_document(None, document_id)
        if "not found" in result.lower():
            raise HTTPException(status_code=404, detail="Document not found")
        return {"content": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve document: {str(e)}")

@app.post("/sessions/{session_id}/clear")
async def clear_session(session_id: str):
    if session_id in conversation_histories:
        del conversation_histories[session_id]
        return {"status": "cleared", "session_id": session_id}
    else:
        return {"status": "not_found", "session_id": session_id}

@app.get("/")
async def root():
    return {
        "service": "RAG Agent API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "chat": "/chat",
            "chat_stream": "/chat/stream",
            "search": "/search",
            "documents": "/documents",
            "clear_session": "/sessions/{session_id}/clear",
        },
        "strategies": ["standard", "multi-query", "reranking", "self-reflection"],
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000)
