from fastapi import APIRouter
from app.models import ConfirmBookingRequest
from app.services.bookings import confirm_booking

router = APIRouter()

@router.post("/confirm-booking")
async def confirm_booking_endpoint(payload: ConfirmBookingRequest):
    return await confirm_booking(
        payload.flight_id,
        payload.passenger_name,
        payload.contact,
        payload.origin_iata,
        payload.dest_iata,
        payload.date
    )
