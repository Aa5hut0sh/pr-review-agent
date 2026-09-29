from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.webhook import router as webhook_router
from app.api.routes import router as routes_router
from app.core.config import settings

app = FastAPI(
    title="AI PR Review Agent API",
    description="Multi-Agent Code Review System using LangGraph and Groq",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook_router, tags=["Webhook"])
app.include_router(routes_router, tags=["Review & Feedback"])


@app.get("/")
def root():
    return {
        "service": "AI PR Review Agent",
        "status": "online",
        "model": settings.groq_model,
        "docs_url": "/docs",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "groq_configured": bool(settings.groq_api_key and "your_groq_api_key" not in settings.groq_api_key),
        "vector_db": settings.qdrant_url,
        "graph_db": settings.neo4j_uri,
    }
