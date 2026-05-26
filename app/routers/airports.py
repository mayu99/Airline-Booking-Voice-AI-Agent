from fastapi import APIRouter
from app.models import AirportQueryRequest
from app.services.airports import resolve_airport

router = APIRouter()

@router.post("/resolve-airport")
async def resolve_airport_endpoint(payload: AirportQueryRequest):
    return resolve_airport(payload.query)
