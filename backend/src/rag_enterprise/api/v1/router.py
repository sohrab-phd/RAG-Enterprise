"""API version 1 routes."""

from fastapi import APIRouter

from rag_enterprise.api.v1.endpoints import health
from rag_enterprise.evaluation.api.routes import router as evaluation_router
from rag_enterprise.generation.api.routes import router as chat_router
from rag_enterprise.knowledge.api.routes import router as knowledge_router
from rag_enterprise.retrieval.api.routes import router as retrieval_router

api_v1_router = APIRouter()
api_v1_router.include_router(health.router, tags=["health"])
api_v1_router.include_router(knowledge_router)
api_v1_router.include_router(retrieval_router)
api_v1_router.include_router(chat_router)
api_v1_router.include_router(evaluation_router)
