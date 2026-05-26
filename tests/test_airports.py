from fastapi.testclient import TestClient
from app.main import app
from app.services.airports import load_airports_data

client = TestClient(app)

# Force load data for tests
load_airports_data()

def test_resolve_airport_lax():
    response = client.post("/resolve-airport", json={"query": "Los Angeles"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "resolved"
    assert data["iata"] == "LAX"
    assert "Los Angeles" in data["airport_name"]
    assert data["city"] == "Los Angeles"
    assert data["confidence"] >= 0.85

def test_ambiguous_airport_new_york():
    response = client.post("/resolve-airport", json={"query": "New York"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ambiguous"
    assert "candidates" in data
    assert len(data["candidates"]) >= 2
    for candidate in data["candidates"]:
        assert "iata" in candidate
        assert "city" in candidate
        assert "country" in candidate

def test_unknown_airport():
    response = client.post("/resolve-airport", json={"query": "xyz123nonsense"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "unknown"
    assert data["query"] == "xyz123nonsense"
