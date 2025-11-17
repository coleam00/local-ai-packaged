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
import asyncpg
from dotenv import load_dotenv

# Load environment variables
load_dotenv(".env")

# Import RAG agent components
from rag_agent_advanced import (
    agent,
    initialize_db,
    close_db,
    search_knowledge_base,
    search_with_multi_query,
    search_with_reranking,
    search_with_self_reflection,
    retrieve_full_document
)

# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Startup
    print("Initializing RAG service...")
    await initialize_db()
    print("✓ RAG service initialized")
    
    yield
    
    # Shutdown
    print("Shutting down RAG service...")
    await close_db()
    print("✓ RAG service shut down")

# Create FastAPI app
app = FastAPI(
    title="RAG Agent API",
    description="Advanced RAG system with multiple retrieval strategies",
    version="1.0.0",
    lifespan=lifespan
)

# Request/Response Models
class ChatRequest(BaseModel):
    """Chat request model."""
    message: str = Field(..., description="User message/query")
    session_id: Optional[str] = Field(default="default", description="Session ID for conversation history")
    strategy: Optional[str] = Field(default="auto", description="RAG strategy: auto, standard, multi-query, reranking, self-reflection")
    stream: bool = Field(default=False, description="Stream response")

class ChatResponse(BaseModel):
    """Chat response model."""
    response: str
    session_id: str
    sources: List[dict] = []
    metadata: dict = {}

class SearchRequest(BaseModel):
    """Direct search request."""
    query: str
    limit: int = Field(default=5, ge=1, le=20)
    strategy: str = Field(default="standard", description="Search strategy")

class SearchResponse(BaseModel):
    """Search response model."""
    results: List[dict]
    query: str
    strategy: str

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    database: str
    agent: str

# Store conversation histories (in-memory, can be replaced with Redis)
conversation_histories = {}

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    try:
        # Check database connection
        from utils.db_utils import db_pool
        async with db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    return HealthResponse(
        status="healthy" if db_status == "healthy" else "degraded",
        database=db_status,
        agent="healthy"
    )

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat with the RAG agent.
    
    This endpoint provides conversational access to the RAG system.
    """
    try:
        # Get or create conversation history
        if request.session_id not in conversation_histories:
            conversation_histories[request.session_id] = []
        
        message_history = conversation_histories[request.session_id]
        
        # Run agent
        result = await agent.run(
            request.message,
            message_history=message_history
        )
        
        # Update conversation history
        conversation_histories[request.session_id] = result.all_messages()
        
        # Extract response
        response_text = result.data if hasattr(result, 'data') else str(result)
        
        return ChatResponse(
            response=response_text,
            session_id=request.session_id,
            sources=[],
            metadata={"strategy": request.strategy}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")

@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Chat with streaming response.
    
    Returns a server-sent events stream.
    """
    async def generate():
        try:
            # Get or create conversation history
            if request.session_id not in conversation_histories:
                conversation_histories[request.session_id] = []
            
            message_history = conversation_histories[request.session_id]
            
            # Stream response
            async with agent.run_stream(
                request.message,
                message_history=message_history
            ) as result:
                async for text in result.stream_text(delta=True):
                    yield f"data: {text}\n\n"
                
                # Update history
                conversation_histories[request.session_id] = result.all_messages()
                
                yield "data: [DONE]\n\n"
                
        except Exception as e:
            yield f"data: Error: {str(e)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )

@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """
    Direct search endpoint without conversation context.
    
    Useful for programmatic access or testing.
    """
    try:
        # Select strategy
        if request.strategy == "multi-query":
            results_text = await search_with_multi_query(None, request.query, request.limit)
        elif request.strategy == "reranking":
            results_text = await search_with_reranking(None, request.query, request.limit)
        elif request.strategy == "self-reflection":
            results_text = await search_with_self_reflection(None, request.query, request.limit)
        else:  # standard
            results_text = await search_knowledge_base(None, request.query, request.limit)
        
        # Parse results (simplified, assumes text format)
        return SearchResponse(
            results=[{"content": results_text}],
            query=request.query,
            strategy=request.strategy
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.get("/documents")
async def list_documents():
    """List all documents in the knowledge base."""
    try:
        from utils.db_utils import db_pool
        
        async with db_pool.acquire() as conn:
            docs = await conn.fetch("""
                SELECT 
                    id::text,
                    title,
                    source,
                    created_at,
                    (SELECT COUNT(*) FROM chunks WHERE document_id = documents.id) as chunk_count
                FROM documents
                ORDER BY created_at DESC
            """)
        
        return [
            {
                "id": doc["id"],
                "title": doc["title"],
                "source": doc["source"],
                "created_at": doc["created_at"].isoformat(),
                "chunk_count": doc["chunk_count"]
            }
            for doc in docs
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")

@app.get("/documents/{document_id}")
async def get_document(document_id: str):
    """Get a specific document by ID."""
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
    """Clear conversation history for a session."""
    if session_id in conversation_histories:
        del conversation_histories[session_id]
        return {"status": "cleared", "session_id": session_id}
    else:
        return {"status": "not_found", "session_id": session_id}

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "RAG Agent API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "chat": "/chat",
            "chat_stream": "/chat/stream",
            "search": "/search",
            "documents": "/documents",
            "clear_session": "/sessions/{session_id}/clear"
        },
        "strategies": [
            "standard",
            "multi-query",
            "reranking",
            "self-reflection"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
