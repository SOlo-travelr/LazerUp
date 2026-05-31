from fastapi import APIRouter

from app.api.v1 import (
    ask,
    bottlenecks,
    founder,
    health,
    linkage,
    markets,
    opportunities,
    reports,
    search,
    trends,
    whitespace,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router, tags=["health"])
api_router.include_router(search.router, tags=["search"])
api_router.include_router(trends.router, tags=["trends"])
api_router.include_router(opportunities.router, tags=["opportunities"])
api_router.include_router(whitespace.router, tags=["white-spaces"])
api_router.include_router(bottlenecks.router, tags=["bottlenecks"])
api_router.include_router(linkage.router, tags=["linkage"])
api_router.include_router(markets.router, tags=["markets"])
api_router.include_router(founder.router, tags=["founder"])
api_router.include_router(ask.router, tags=["ask"])
api_router.include_router(reports.router, tags=["reports"])
