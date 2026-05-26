from fastapi import APIRouter, BackgroundTasks
from app.models import SendConfirmationRequest
from app.services.notifications import prepare_notification, send_twilio_sms_sync, send_resend_email_sync
from app.config import settings

router = APIRouter()

@router.post("/send-confirmation")
async def send_confirmation_endpoint(payload: SendConfirmationRequest, background_tasks: BackgroundTasks):
    contact = payload.contact.strip()
    channel, res_data = prepare_notification(payload.confirmation_number, contact, payload.passenger_name)
    
    if channel == "invalid":
        return {"status": "invalid_contact"}
        
    if channel == "sms":
        # Twilio Trial restrictions check
        if contact != settings.MY_TEST_PHONE:
            return {
                "status": "sent_simulated",
                "channel": "sms",
                "reason": "trial_unverified_number",
                "note": "Logged for demo — recipient must be verified in Twilio trial console."
            }
        # Verified contact: process in background task
        background_tasks.add_task(send_twilio_sms_sync, contact, res_data["sms_text"])
        return {
            "status": "sent",
            "channel": "sms",
            "destination_masked": res_data["destination_masked"]
        }
        
    elif channel == "email":
        # Always use background task for emails
        background_tasks.add_task(send_resend_email_sync, contact, res_data["email_subject"], res_data["email_body"])
        return {
            "status": "sent",
            "channel": "email",
            "destination_masked": res_data["destination_masked"]
        }
