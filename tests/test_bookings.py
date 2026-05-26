import json
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def read_fixture(name: str) -> dict:
    with open(f"tests/fixtures/{name}", "r") as f:
        return json.load(f)

@pytest.mark.asyncio
@patch("app.services.bookings.airline_client.book_flight", new_callable=AsyncMock)
@patch("app.services.bookings.airline_client.search_flights", new_callable=AsyncMock)
async def test_booking_splits_name_mayuresh_choudhary(mock_search, mock_book):
    mock_search.return_value = read_fixture("upstream_flights_ok.json")
    mock_book.return_value = read_fixture("upstream_booking_ok.json")
    
    response = client.post("/confirm-booking", json={
        "flight_id": "39023fbe9e64da5b7407eea7898c9762",
        "passenger_name": "Mayuresh Choudhary",
        "contact": "+14155551234",
        "origin_iata": "JFK",
        "dest_iata": "LAX",
        "date": "2026-07-15"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "confirmed"
    assert data["confirmation_number"] == "CONF154648"
    assert "flight_summary" in data
    
    mock_book.assert_called_once_with(
        "39023fbe9e64da5b7407eea7898c9762",
        "Mayuresh",
        "Choudhary",
        "2026-07-15"
    )

@pytest.mark.asyncio
@patch("app.services.bookings.airline_client.book_flight", new_callable=AsyncMock)
@patch("app.services.bookings.airline_client.search_flights", new_callable=AsyncMock)
async def test_booking_single_name_uses_guest_lastname(mock_search, mock_book):
    mock_search.return_value = read_fixture("upstream_flights_ok.json")
    mock_book.return_value = {
        "success": True,
        "confirmationNumber": "CONF111222",
        "flightId": "39023fbe9e64da5b7407eea7898c9762",
        "passenger": {"firstName": "Mayuresh", "lastName": "Guest"}
    }
    
    response = client.post("/confirm-booking", json={
        "flight_id": "39023fbe9e64da5b7407eea7898c9762",
        "passenger_name": "Mayuresh",
        "contact": "+14155551234",
        "origin_iata": "JFK",
        "dest_iata": "LAX",
        "date": "2026-07-15"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "confirmed"
    assert data["confirmation_number"] == "CONF111222"
    
    mock_book.assert_called_once_with(
        "39023fbe9e64da5b7407eea7898c9762",
        "Mayuresh",
        "Guest",
        "2026-07-15"
    )

def test_confirmation_number_phonetic_spelling():
    from app.services.bookings import get_nato_phonetic
    assert get_nato_phonetic("CONF154648") == "Charlie, Oscar, November, Foxtrot, 1, 5, 4, 6, 4, 8"
    assert get_nato_phonetic("AB12") == "Alpha, Bravo, 1, 2"
