from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import MarketCapitalMapOut
from app.services.markets import get_market_capital_map

router = APIRouter()


@router.get("/investor/map", response_model=MarketCapitalMapOut)
def investor_map(
    days: int = 180,
    sectors: int = 10,
    hotspots: int = 12,
    db: Session = Depends(get_db),
) -> MarketCapitalMapOut:
    return get_market_capital_map(db, days=days, sectors=sectors, hotspots=hotspots)
