import json
import pytest
import datetime
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def read_fixture(name: str) -> dict:
    with open(f"tests/fixtures/{name}", "r") as f:
        return json.load(f)

@pytest.mark.asyncio
@patch("app.services.flights.airline_client.search_flights", new_callable=AsyncMock)
async def test_jfk_to_lax_returns_flights(mock_search):
    mock_search.return_value = read_fixture("upstream_flights_ok.json")
    
    future_date = (datetime.date.today() + datetime.timedelta(days=50)).isoformat()
    
    response = client.post("/check-flights", json={
        "origin_iata": "JFK",
        "dest_iata": "LAX",
        "date": future_date
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "available"
    assert "voice_preamble" in data
    assert len(data["flights"]) > 0
    
    f = data["flights"][0]
    assert f["flight_id"] == "3c577ea13f6b8b1f52a361c187c34fb1"
    assert f["airline"] == "JetBlue Airways"
    assert f["flight_number"] == "JA927"
    assert f["depart"] == "1:01 PM"
    assert f["arrive"] == "6:31 PM"
    assert f["duration"] == "5 hours 30 minutes"
    assert f["stops"] == "nonstop"
    assert f["price_usd"] == 493.85
    assert "summary" in f
    assert "JetBlue Airways JA927, nonstop, departs 1:01 PM arrives 6:31 PM, 5 hours 30 minutes, $493" in f["summary"]

@pytest.mark.asyncio
@patch("app.services.flights.airline_client.search_flights", new_callable=AsyncMock)
async def test_aal_to_yvr_upstream_404_returns_no_flights_envelope(mock_search):
    mock_search.return_value = read_fixture("upstream_flights_404.json")
    
    future_date = (datetime.date.today() + datetime.timedelta(days=50)).isoformat()
    
    response = client.post("/check-flights", json={
        "origin_iata": "AAL",
        "dest_iata": "YVR",
        "date": future_date
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "no_flights"
    assert "no flights available" in data["message"]

def test_invalid_date_past_does_not_hit_upstream():
    past_date = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    
    with patch("app.services.flights.airline_client.search_flights", new_callable=AsyncMock) as mock_search:
        response = client.post("/check-flights", json={
            "origin_iata": "JFK",
            "dest_iata": "LAX",
            "date": past_date
        })
        mock_search.assert_not_called()
        
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "invalid_date"
    assert "The date must be between today" in data["message"]

def test_invalid_date_future_does_not_hit_upstream():
    future_date = (datetime.date.today() + datetime.timedelta(days=366)).isoformat()
    
    with patch("app.services.flights.airline_client.search_flights", new_callable=AsyncMock) as mock_search:
        response = client.post("/check-flights", json={
            "origin_iata": "JFK",
            "dest_iata": "LAX",
            "date": future_date
        })
        mock_search.assert_not_called()
        
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "invalid_date"
    assert "The date must be between today" in data["message"]
