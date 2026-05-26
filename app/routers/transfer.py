from fastapi import APIRouter
from app.models import TransferRequest
from app.services.transfer import initiate_transfer

router = APIRouter()

@router.post("/transfer")
async def transfer_endpoint(payload: TransferRequest):
    return initiate_transfer(payload.call_context, payload.session_id)
