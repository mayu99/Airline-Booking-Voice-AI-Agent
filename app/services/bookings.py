import logging
from typing import Dict, Any
from app.upstream.airline_client import airline_client
from app.services.flights import format_time_for_voice

logger = logging.getLogger("bookings_service")

# Global in-memory booking database
bookings_db: Dict[str, Dict[str, Any]] = {}

NATO_PHONETIC = {
    'A': 'Alpha', 'B': 'Bravo', 'C': 'Charlie', 'D': 'Delta', 'E': 'Echo',
    'F': 'Foxtrot', 'G': 'Golf', 'H': 'Hotel', 'I': 'India', 'J': 'Juliet',
    'K': 'Kilo', 'L': 'Lima', 'M': 'Mike', 'N': 'November', 'O': 'Oscar',
    'P': 'Papa', 'Q': 'Quebec', 'R': 'Romeo', 'S': 'Sierra', 'T': 'Tango',
    'U': 'Uniform', 'V': 'Victor', 'W': 'Whiskey', 'X': 'Xray', 'Y': 'Yankee',
    'Z': 'Zulu'
}

def get_nato_phonetic(code: str) -> str:
    """
    Generates NATO phonetic spelling for confirmation numbers.
    Spells out letters (A-Z) and keeps numbers (0-9) as-is.
    Composed as comma-separated string, e.g. "Charlie, Oscar, 1, 5"
    """
    parts = []
    for char in code:
        char_upper = char.upper()
        if char_upper in NATO_PHONETIC:
            parts.append(NATO_PHONETIC[char_upper])
        else:
            parts.append(char)
    return ", ".join(parts)

async def confirm_booking(
    flight_id: str,
    passenger_name: str,
    contact: str,
    origin_iata: str,
    dest_iata: str,
    date: str
) -> Dict[str, Any]:
    """
    Splits passenger name, POSTs to upstream, retrieves flight details for summary,
    stores booking in database, and returns confirmation details with NATO phonetics.
    """
    # 1. Split passenger name
    name_stripped = passenger_name.strip()
    if " " in name_stripped:
        first_name, last_name = name_stripped.rsplit(" ", 1)
    else:
        first_name = name_stripped
        last_name = "Guest"
        logger.warning(f"Single word name provided: '{passenger_name}'. Setting lastName to 'Guest'.")

    # 2. Fetch flight details from upstream to populate flight_summary
    flight_detail = None
    try:
        search_res = await airline_client.search_flights(origin_iata, dest_iata, date)
        for f in search_res.get("flights", []):
            if f.get("flightId") == flight_id:
                flight_detail = f
                break
    except Exception as e:
        logger.error(f"Failed to fetch flight details for validation/summary: {e}")

    # 3. Call upstream booking API
    try:
        booking_res = await airline_client.book_flight(flight_id, first_name, last_name, date)
    except Exception as e:
        logger.error(f"Upstream booking failed: {e}")
        return {
            "status": "booking_failed",
            "message": "I couldn't complete that booking. The seat may have just been taken. Would you like to try another flight?"
        }

    # 4. Process success response
    success = booking_res.get("success", False)
    if not success:
        return {
            "status": "booking_failed",
            "message": "I couldn't complete that booking. The seat may have just been taken. Would you like to try another flight?"
        }

    conf_num = booking_res.get("confirmationNumber", "CONF000000")
    phonetic_conf = get_nato_phonetic(conf_num)

    # Resolve default summary fields if search was empty or missing
    airline = "Unknown Airline"
    flight_number = "Unknown Flight"
    depart_time = "12:00 PM"
    arrive_time = "12:00 PM"
    if flight_detail:
        airline = flight_detail.get("airline", airline)
        flight_number = flight_detail.get("flightNumber", flight_number)
        depart_time = format_time_for_voice(flight_detail.get("departureTime", ""))
        arrive_time = format_time_for_voice(flight_detail.get("arrivalTime", ""))

    flight_summary = {
        "airline": airline,
        "flight_number": flight_number,
        "origin_iata": origin_iata.upper(),
        "dest_iata": dest_iata.upper(),
        "date": date,
        "depart": depart_time,
        "arrive": arrive_time
    }

    # 5. Store in global memory db
    bookings_db[conf_num] = {
        "confirmation_number": conf_num,
        "passenger_name": passenger_name,
        "contact": contact,
        "airline": airline,
        "flight_number": flight_number,
        "origin_iata": origin_iata.upper(),
        "dest_iata": dest_iata.upper(),
        "date": date,
        "depart": depart_time
    }

    return {
        "status": "confirmed",
        "confirmation_number": conf_num,
        "phonetic_confirmation": phonetic_conf,
        "flight_summary": flight_summary
    }
