import pytest
import os
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

TEST_LOG_PATH = os.path.abspath("test/logs/test_syslog.log")

def test_tick_endpoint():
    response = client.post("/tick", json={
        "channel_id": "cron jobs",
        "return_url": "https://ping.telex.im/v1/webhooks/019537ae-6f4b-7a7b-94b6-011175b27f96",
        "settings": [{"label": "cron_log_path", "type": "dropdown", "required": True, "default": TEST_LOG_PATH}]
    })

    assert response.status_code == 202, f"Unexpected response: {response.text}" # Ensure correct response
    assert "message" in response.json(), "Missing message in response JSON"
