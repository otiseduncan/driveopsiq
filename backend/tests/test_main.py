"""Smoke tests for core application endpoints."""

import pytest


pytestmark = pytest.mark.asyncio


async def test_root_health(async_client):
    response = await async_client.get("/health")
    assert response.status_code == 200


async def test_api_root(async_client):
    response = await async_client.get("/")
    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "SyferStack API"
