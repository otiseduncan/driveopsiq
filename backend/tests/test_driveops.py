"""Integration tests for DriveOps IQ endpoints."""

import pytest
from uuid import uuid4


pytestmark = pytest.mark.asyncio


async def test_driveops_flow_requires_auth(async_client):
    # Attempt to create request without credentials
    response = await async_client.post(
        "/api/v1/driveops/requests",
        json={
            "ro_number": "RO-1001",
            "vin": "1FTFW1ET1EFA00001",
            "customer": "Test Customer",
            "insurer": "Test Insurer",
            "calibration_type": "ADAS Calibration",
            "notes": "Initial attempt",
        },
    )

    assert response.status_code == 403


async def test_driveops_request_crud(async_client):
    register_payload = {
        "email": f"tech-{uuid4().hex}@example.com",
        "full_name": "Drive Ops Tech",
        "password": "StrongPass123!",
    }

    register_response = await async_client.post(
        "/api/v1/auth/register", json=register_payload
    )
    assert register_response.status_code == 201

    login_response = await async_client.post(
        "/api/v1/auth/login/json",
        json={"email": register_payload["email"], "password": register_payload["password"]},
    )
    assert login_response.status_code == 200
    tokens = login_response.json()
    assert "access_token" in tokens
    auth_header = {"Authorization": f"Bearer {tokens['access_token']}"}

    create_payload = {
        "ro_number": f"RO-{uuid4().hex[:8]}",
        "vin": "1HGCM82633A004352",
        "customer": "Acme Collision",
        "insurer": "Syfer Insurance",
        "calibration_type": "Camera Calibration",
        "notes": "Requires calibration after windshield replacement",
    }

    create_response = await async_client.post(
        "/api/v1/driveops/requests",
        json=create_payload,
        headers=auth_header,
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["request"]["status"] == "pending_validation"

    duplicate_response = await async_client.post(
        "/api/v1/driveops/requests",
        json=create_payload,
        headers=auth_header,
    )
    assert duplicate_response.status_code == 409

    list_response = await async_client.get("/api/v1/driveops/requests", headers=auth_header)
    assert list_response.status_code == 200
    requests = list_response.json()
    matching = [req for req in requests if req["ro_number"] == create_payload["ro_number"]]
    assert matching, "Expected created request to be present in listing"

    detail_response = await async_client.get(
        f"/api/v1/driveops/requests/{created['request']['id']}", headers=auth_header
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["vin"] == create_payload["vin"]
