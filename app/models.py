from pydantic import BaseModel, Field
from typing import List, Optional

# --- Resolving Airport Models ---
class AirportQueryRequest(BaseModel):
    query: str

class AirportCandidate(BaseModel):
    iata: str
    city: str
    country: str

class AirportResolvedResponse(BaseModel):
    status: str = "resolved"
    iata: str
    airport_name: str
    city: str
    country: str
    confidence: float

class AirportAmbiguousResponse(BaseModel):
    status: str = "ambiguous"
    candidates: List[AirportCandidate]

class AirportUnknownResponse(BaseModel):
    status: str = "unknown"
    query: str

# --- Checking Flights Models ---
class CheckFlightsRequest(BaseModel):
    origin_iata: str
    dest_iata: str
    date: str

class FlightSchema(BaseModel):
    flight_id: str
    airline: str
    flight_number: str
    depart: str
    arrive: str
    duration: str
    stops: str
    price_usd: float
    summary: str

class CheckFlightsAvailableResponse(BaseModel):
    status: str = "available"
    voice_preamble: str
    flights: List[FlightSchema]

class CheckFlightsErrorResponse(BaseModel):
    status: str
    message: str

# --- Confirming Booking Models ---
class ConfirmBookingRequest(BaseModel):
    flight_id: str
    passenger_name: str
    contact: str
    origin_iata: str
    dest_iata: str
    date: str

class FlightSummary(BaseModel):
    airline: str
    flight_number: str
    origin_iata: str
    dest_iata: str
    date: str
    depart: str
    arrive: str

class ConfirmBookingSuccessResponse(BaseModel):
    status: str = "confirmed"
    confirmation_number: str
    phonetic_confirmation: str
    flight_summary: FlightSummary

class ConfirmBookingErrorResponse(BaseModel):
    status: str = "booking_failed"
    message: str

# --- Sending Confirmation Models ---
class SendConfirmationRequest(BaseModel):
    confirmation_number: str
    contact: str
    passenger_name: str

class SendConfirmationSuccessResponse(BaseModel):
    status: str = "sent"
    channel: str
    destination_masked: str

class SendConfirmationSimulatedResponse(BaseModel):
    status: str = "sent_simulated"
    channel: str = "sms"
    reason: str = "trial_unverified_number"
    note: str = "Logged for demo — recipient must be verified in Twilio trial console."

# --- Transfer Models ---
class TransferRequest(BaseModel):
    call_context: str
    session_id: str

class TransferResponse(BaseModel):
    status: str = "transfer_initiated"
    transfer_number: str
    handoff_summary: str
