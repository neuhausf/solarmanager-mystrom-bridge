"""Tests for the MyStromBridgeCoordinator."""
from __future__ import annotations

import pytest
from aioresponses import aioresponses

from custom_components.solarmanager_mystrom_bridge.coordinator import (
    MyStromBridgeCoordinator,
)
from custom_components.solarmanager_mystrom_bridge.const import DOMAIN

HOST = "192.168.1.201"
BASE_URL = f"http://{HOST}"


@pytest.mark.asyncio
async def test_coordinator_fetches_report(hass, aiohttp_client):
    """Coordinator._async_update_data returns parsed JSON from /report."""
    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    session = async_get_clientsession(hass)

    with aioresponses() as mock_aio:
        mock_aio.get(
            f"{BASE_URL}/report",
            payload={"power": 12.5, "relay": True},
        )
        coordinator = MyStromBridgeCoordinator(hass, session, HOST, scan_interval=5)
        data = await coordinator._async_update_data()

    assert data == {"power": 12.5, "relay": True}


@pytest.mark.asyncio
async def test_coordinator_raises_on_connection_error(hass):
    """Coordinator raises UpdateFailed when device is unreachable."""
    from aiohttp import ClientConnectionError
    from homeassistant.helpers.aiohttp_client import async_get_clientsession
    from homeassistant.helpers.update_coordinator import UpdateFailed

    session = async_get_clientsession(hass)

    with aioresponses() as mock_aio:
        mock_aio.get(
            f"{BASE_URL}/report",
            exception=ClientConnectionError("unreachable"),
        )
        coordinator = MyStromBridgeCoordinator(hass, session, HOST, scan_interval=5)
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_coordinator_set_relay_on(hass):
    """async_set_relay(True) calls /relay?state=1."""
    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    session = async_get_clientsession(hass)
    coordinator = MyStromBridgeCoordinator(hass, session, HOST, scan_interval=5)

    with aioresponses() as mock_aio:
        mock_aio.get(f"{BASE_URL}/relay", payload={"relay": True})
        await coordinator.async_set_relay(True)

    # Verify the call was made with state=1
    request_list = mock_aio.requests
    assert len(request_list) == 1
    request_call = list(request_list.values())[0][0]
    # The URL passed to the mock includes query parameters
    called_url = str(list(request_list.keys())[0][1])
    assert "state=1" in called_url


@pytest.mark.asyncio
async def test_coordinator_set_relay_off(hass):
    """async_set_relay(False) calls /relay?state=0."""
    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    session = async_get_clientsession(hass)
    coordinator = MyStromBridgeCoordinator(hass, session, HOST, scan_interval=5)

    with aioresponses() as mock_aio:
        mock_aio.get(f"{BASE_URL}/relay", payload={"relay": False})
        await coordinator.async_set_relay(False)

    request_list = mock_aio.requests
    assert len(request_list) == 1
    called_url = str(list(request_list.keys())[0][1])
    assert "state=0" in called_url


@pytest.mark.asyncio
async def test_coordinator_set_power(hass):
    """async_set_power posts to /power with correct JSON body."""
    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    session = async_get_clientsession(hass)
    coordinator = MyStromBridgeCoordinator(hass, session, HOST, scan_interval=5)

    with aioresponses() as mock_aio:
        mock_aio.post(f"{BASE_URL}/power", payload={})
        await coordinator.async_set_power(42.0)

    request_list = mock_aio.requests
    assert len(request_list) == 1
    request_call = list(request_list.values())[0][0]
    assert request_call.kwargs["json"] == {"power": 42.0}
