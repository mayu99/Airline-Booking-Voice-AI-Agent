import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings

client = TestClient(app)

def test_sms_routed_for_us_number():
    with patch("app.routers.notifications.send_twilio_sms_sync") as mock_sms:
        response = client.post("/send-confirmation", json={
            "confirmation_number": "CONF154648",
            "contact": settings.MY_TEST_PHONE,
            "passenger_name": "Mayuresh Choudhary"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "sent"
        assert data["channel"] == "sms"
        mock_sms.assert_called_once()

def test_email_routed_for_non_us_contact():
    with patch("app.routers.notifications.send_resend_email_sync") as mock_email:
        response = client.post("/send-confirmation", json={
            "confirmation_number": "CONF154648",
            "contact": "mayuresh@example.com",
            "passenger_name": "Mayuresh Choudhary"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "sent"
        assert data["channel"] == "email"
        mock_email.assert_called_once()

def test_twilio_trial_error_21608_returns_sent_simulated():
    # Pass a number distinct from MY_TEST_PHONE to trigger simulation return
    unverified_phone = "+14155559999"
    assert unverified_phone != settings.MY_TEST_PHONE
    
    response = client.post("/send-confirmation", json={
        "confirmation_number": "CONF154648",
        "contact": unverified_phone,
        "passenger_name": "Mayuresh Choudhary"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "sent_simulated"
    assert data["channel"] == "sms"
    assert data["reason"] == "trial_unverified_number"

def test_healthz_returns_200():
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "uptime_seconds" in data
