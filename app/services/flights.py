import datetime
import logging
from datetime import datetime as dt_class
from typing import Dict, Any, Union
from app.upstream.airline_client import airline_client

logger = logging.getLogger("flights_service")

def validate_date(date_str: str) -> bool:
    """
    Validates that a date is in the format YYYY-MM-DD and falls between
    today and today + 365 days.
    """
    try:
        parsed_date = datetime.date.fromisoformat(date_str)
        today = datetime.date.today()
        # Allow today <= date <= today + 365 days
        return today <= parsed_date <= today + datetime.timedelta(days=365)
    except ValueError:
        return False

def format_time_for_voice(iso_str: str) -> str:
    """
    Converts ISO 8601 UTC string (e.g. 2026-07-15T13:01:00.000Z)
    into a voice-friendly 12-hour clock string (e.g. 1:01 PM).
    """
    try:
        cleaned = iso_str.replace("Z", "+00:00")
        parsed = dt_class.fromisoformat(cleaned)
        formatted = parsed.strftime("%I:%M %p")
        # Strip leading zero if present (e.g. "01:01 PM" -> "1:01 PM")
        if formatted.startswith("0"):
            formatted = formatted[1:]
        return formatted
    except Exception as e:
        logger.error(f"Error parsing time {iso_str}: {e}")
        return iso_str

def format_duration(minutes: int) -> str:
    """
    Converts duration minutes to "X hours Y minutes".
    """
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours} hours {mins} minutes"

def format_date_for_voice(date_str: str) -> str:
    """
    Converts a date string YYYY-MM-DD to a format like "July 15th".
    """
    try:
        parsed = dt_class.strptime(date_str, "%Y-%m-%d")
        day = parsed.day
        if 11 <= day <= 13:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
        return parsed.strftime(f"%B {day}{suffix}")
    except Exception:
        return date_str

async def check_flights(origin_iata: str, dest_iata: str, date: str) -> Dict[str, Any]:
    """
    Performs flight searches after validating the date locally.
    Returns structured results for available, no flights, or error states.
    """
    # 1. Validate date locally first
    if not validate_date(date):
        return {
            "status": "invalid_date",
            "message": "The date must be between today and one year from now. What date would you like to fly?"
        }

    # 2. Query upstream client
    try:
        upstream_data = await airline_client.search_flights(origin_iata, dest_iata, date)
    except Exception as e:
        logger.error(f"Upstream flight search failed: {e}")
        return {
            "status": "upstream_error",
            "message": "I'm having trouble reaching our flight system. Please try again in a moment."
        }

    flights_list = upstream_data.get("flights", [])
    if not flights_list:
        return {
            "status": "no_flights",
            "message": "I'm sorry, no flights available on that route. Can I try a different date?"
        }

    # 3. Process each flight into voice-friendly format
    processed_flights = []
    for f in flights_list:
        flight_id = f.get("flightId")
        airline = f.get("airline")
        flight_number = f.get("flightNumber")
        departure_time = f.get("departureTime")
        arrival_time = f.get("arrivalTime")
        duration_minutes = f.get("durationMinutes", 0)
        stops_count = f.get("stops", 0)
        price = f.get("price", 0.0)

        depart_voice = format_time_for_voice(departure_time)
        arrive_voice = format_time_for_voice(arrival_time)
        duration_voice = format_duration(duration_minutes)
        stops_voice = "nonstop" if stops_count == 0 else (f"1 stop" if stops_count == 1 else f"{stops_count} stops")
        
        # summary: "JetBlue JA927, nonstop, departs 1:01 PM arrives 6:31 PM, 5 hours 30 minutes, $493"
        price_int = int(price)
        summary = f"{airline} {flight_number}, {stops_voice}, departs {depart_voice} arrives {arrive_voice}, {duration_voice}, ${price_int}"

        processed_flights.append({
            "flight_id": flight_id,
            "airline": airline,
            "flight_number": flight_number,
            "depart": depart_voice,
            "arrive": arrive_voice,
            "duration": duration_voice,
            "stops": stops_voice,
            "price_usd": round(price, 2),
            "summary": summary
        })

    formatted_date = format_date_for_voice(date)
    voice_preamble = f"I found {len(processed_flights)} flights from {origin_iata.upper()} to {dest_iata.upper()} on {formatted_date}."

    return {
        "status": "available",
        "voice_preamble": voice_preamble,
        "flights": processed_flights
    }
