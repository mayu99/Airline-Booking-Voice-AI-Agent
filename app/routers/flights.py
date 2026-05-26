from fastapi import APIRouter
from app.models import CheckFlightsRequest
from app.services.flights import check_flights

router = APIRouter()

@router.post("/check-flights")
async def check_flights_endpoint(payload: CheckFlightsRequest):
    return await check_flights(payload.origin_iata, payload.dest_iata, payload.date)
