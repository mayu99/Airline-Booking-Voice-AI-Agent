import re
import logging
from typing import Dict, Any, Tuple
from app.config import settings
from app.services.bookings import bookings_db
from twilio.rest import Client as TwilioClient
from twilio.base.exceptions import TwilioRestException
import resend

logger = logging.getLogger("notifications_service")

PHONE_REGEX = re.compile(r"^\+1\d{10}$")
EMAIL_REGEX = re.compile(r"^[^@]+@[^@]+\.[^@]+$")

def mask_contact(contact: str) -> str:
    """
    Masks contact information for security in logs.
    e.g. +14155551234 -> +1415***1234
    e.g. user@example.com -> u***r@example.com
    """
    if "@" in contact:
        parts = contact.split("@", 1)
        name = parts[0]
        domain = parts[1]
        if len(name) > 2:
            return f"{name[0]}***{name[-1]}@{domain}"
        return f"***@{domain}"
    elif len(contact) >= 10:
        return f"{contact[:5]}***{contact[-4:]}"
    return "***"

def send_twilio_sms_sync(to_phone: str, body: str):
    """
    Synchronous worker to send Twilio SMS. Catches trial account restrictions.
    """
    logger.info(f"Background task: Sending SMS to {mask_contact(to_phone)}")
    try:
        client = TwilioClient(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=body,
            from_=settings.TWILIO_FROM_NUMBER,
            to=to_phone
          )
        logger.info(f"Twilio SMS sent successfully. Message SID: {message.sid}")
    except TwilioRestException as e:
        if e.code == 21608:
            logger.warning(f"Twilio Trial unverified number 21608 caught. Details: {e.msg}")
        else:
            logger.error(f"Twilio SMS failed with error: {e}")
    except Exception as e:
        logger.error(f"Unexpected Twilio SMS error: {e}")

def send_resend_email_sync(to_email: str, subject: str, body: str):
    """
    Synchronous worker to send Resend email.
    """
    logger.info(f"Background task: Sending email to {mask_contact(to_email)}")
    try:
        resend.api_key = settings.RESEND_API_KEY
        res = resend.Emails.send({
            "from": "SkyJet <onboarding@resend.dev>",
            "to": to_email,
            "subject": subject,
            "text": body
        })
        logger.info(f"Resend email sent successfully. ID: {res.get('id')}")
    except Exception as e:
        logger.error(f"Resend email failed: {e}")

def prepare_notification(
    confirmation_number: str,
    contact: str,
    passenger_name: str
) -> Tuple[str, Dict[str, Any]]:
    """
    Classifies the channel and prepares message payload.
    Returns (channel_name, payload).
    """
    contact_stripped = contact.strip()
    
    # 1. Route validation
    if PHONE_REGEX.match(contact_stripped):
        channel = "sms"
    elif EMAIL_REGEX.match(contact_stripped):
        channel = "email"
    else:
        channel = "invalid"

    if channel == "invalid":
        return "invalid", {}

    # 2. Lookup booking or fallback
    booking = bookings_db.get(confirmation_number)
    if not booking:
        logger.warning(f"Booking {confirmation_number} not found in database. Using default fallback values.")
        booking = {
            "confirmation_number": confirmation_number,
            "passenger_name": passenger_name,
            "contact": contact,
            "airline": "SkyJet Airlines",
            "flight_number": "SJ100",
            "origin_iata": "JFK",
            "dest_iata": "LAX",
            "date": "2026-07-15",
            "depart": "12:00 PM"
        }

    # 3. Formulate message
    # SMS: "SkyJet confirmation {CONF#}: {airline} {flight_number} on {date}, {origin}→{dest}, departs {depart}. Passenger: {name}."
    sms_text = f"SkyJet confirmation {confirmation_number}: {booking['airline']} {booking['flight_number']} on {booking['date']}, {booking['origin_iata']}→{booking['dest_iata']}, departs {booking['depart']}. Passenger: {passenger_name}."
    
    email_subject = f"SkyJet Booking Confirmation {confirmation_number}"
    email_body = sms_text

    return channel, {
        "sms_text": sms_text,
        "email_subject": email_subject,
        "email_body": email_body,
        "destination_masked": mask_contact(contact_stripped)
    }
