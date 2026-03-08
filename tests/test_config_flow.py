"""Tests for the SolarManager MyStrom Bridge config flow."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from custom_components.solarmanager_mystrom_bridge.const import DOMAIN

HOST = "192.168.1.201"
NAME = "Virtual Switch 1"


async def test_config_flow_success(hass):
    """Full happy-path: user step + power step → entry created."""
    with patch(
        "custom_components.solarmanager_mystrom_bridge.config_flow._validate_host",
        new=AsyncMock(return_value=None),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        assert result["type"] == "form"
        assert result["step_id"] == "user"

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "name": NAME,
                "host": HOST,
                "scan_interval": 5,
            },
        )
        assert result2["type"] == "form"
        assert result2["step_id"] == "power"

        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            {},  # no power entity
        )
        assert result3["type"] == "create_entry"
        assert result3["title"] == NAME
        assert result3["data"]["host"] == HOST
        assert result3["data"]["scan_interval"] == 5
        assert "power_entity_id" not in result3["data"]


async def test_config_flow_with_power_entity(hass):
    """Config flow stores power_entity_id when provided."""
    with patch(
        "custom_components.solarmanager_mystrom_bridge.config_flow._validate_host",
        new=AsyncMock(return_value=None),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"name": NAME, "host": HOST, "scan_interval": 10},
        )
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            {"power_entity_id": "sensor.solar_power"},
        )
        assert result3["type"] == "create_entry"
        assert result3["data"]["power_entity_id"] == "sensor.solar_power"
        assert result3["data"]["scan_interval"] == 10


async def test_config_flow_with_controlled_entity(hass):
    """Config flow stores controlled_entity_id when provided."""
    with patch(
        "custom_components.solarmanager_mystrom_bridge.config_flow._validate_host",
        new=AsyncMock(return_value=None),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"name": NAME, "host": HOST, "scan_interval": 5},
        )
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            {"controlled_entity_id": "switch.living_room"},
        )
        assert result3["type"] == "create_entry"
        assert result3["data"]["controlled_entity_id"] == "switch.living_room"
        assert "power_entity_id" not in result3["data"]


    """User sees an error when the device is unreachable."""
    import aiohttp

    with patch(
        "custom_components.solarmanager_mystrom_bridge.config_flow._validate_host",
        side_effect=aiohttp.ClientConnectionError,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"name": NAME, "host": "bad-host", "scan_interval": 5},
        )
        assert result2["type"] == "form"
        assert result2["errors"]["base"] == "cannot_connect"


async def test_config_flow_abort_already_configured(hass):
    """Config flow aborts when the same host is already configured."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(
        domain=DOMAIN,
        title=NAME,
        data={"host": HOST, "name": NAME, "scan_interval": 5},
        unique_id=HOST.lower(),
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.solarmanager_mystrom_bridge.config_flow._validate_host",
        new=AsyncMock(return_value=None),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"name": NAME, "host": HOST, "scan_interval": 5},
        )
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            {},
        )
        assert result3["type"] == "abort"
        assert result3["reason"] == "already_configured"
