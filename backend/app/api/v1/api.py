from fastapi import APIRouter

from app.api.v1.endpoints import tenders, users, auth, awards, scrapers, enrichment

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(tenders.router, prefix="/tenders", tags=["tenders"])
api_router.include_router(awards.router, prefix="/awards", tags=["awards"])
api_router.include_router(scrapers.router, prefix="/scrapers", tags=["scrapers"])
api_router.include_router(enrichment.router, prefix="/enrichment", tags=["enrichment"]) 