from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import MarketCapitalMapOut, MarketHeadlinesOut
from app.services.markets import get_market_capital_map, get_market_headlines

router = APIRouter()


@router.get("/markets/headlines", response_model=MarketHeadlinesOut)
def market_headlines(
    days: int = 90,
    per_region: int = 6,
    db: Session = Depends(get_db),
) -> MarketHeadlinesOut:
    return get_market_headlines(db, days=days, per_region=per_region)


@router.get("/markets/capital-map", response_model=MarketCapitalMapOut)
def market_capital_map(
    days: int = 180,
    sectors: int = 10,
    hotspots: int = 12,
    db: Session = Depends(get_db),
) -> MarketCapitalMapOut:
    return get_market_capital_map(db, days=days, sectors=sectors, hotspots=hotspots)
