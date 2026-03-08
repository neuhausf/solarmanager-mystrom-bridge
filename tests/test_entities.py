"""Tests for switch and sensor entities."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.solarmanager_mystrom_bridge.const import DOMAIN

HOST = "192.168.1.201"
NAME = "Virtual Switch 1"


def _make_entry(hass, **extra) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=NAME,
        data={"host": HOST, "name": NAME, "scan_interval": 5, **extra},
        unique_id=HOST.lower(),
    )
    entry.add_to_hass(hass)
    return entry


async def _setup_entry(hass, entry):
    """Patch coordinator refresh and set up the config entry."""
    with patch(
        "custom_components.solarmanager_mystrom_bridge.coordinator."
        "MyStromBridgeCoordinator._async_update_data",
        return_value={"power": 25.0, "relay": True},
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()


async def test_switch_state_on(hass):
    """Switch entity reflects relay=True from coordinator data."""
    entry = _make_entry(hass)
    await _setup_entry(hass, entry)

    state = hass.states.get(f"switch.{NAME.lower().replace(' ', '_')}")
    assert state is not None
    assert state.state == "on"


async def test_switch_state_off(hass):
    """Switch entity reflects relay=False from coordinator data."""
    entry = _make_entry(hass)
    with patch(
        "custom_components.solarmanager_mystrom_bridge.coordinator."
        "MyStromBridgeCoordinator._async_update_data",
        return_value={"power": 0.0, "relay": False},
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get(f"switch.{NAME.lower().replace(' ', '_')}")
    assert state is not None
    assert state.state == "off"


async def test_switch_turn_on_calls_relay(hass):
    """Calling turn_on on the switch calls async_set_relay(True)."""
    entry = _make_entry(hass)
    await _setup_entry(hass, entry)

    coordinator = hass.data[DOMAIN][entry.entry_id]
    coordinator.async_set_relay = AsyncMock()

    await hass.services.async_call(
        "switch",
        "turn_on",
        {"entity_id": f"switch.{NAME.lower().replace(' ', '_')}"},
        blocking=True,
    )
    coordinator.async_set_relay.assert_awaited_once_with(True)


async def test_switch_turn_off_calls_relay(hass):
    """Calling turn_off on the switch calls async_set_relay(False)."""
    entry = _make_entry(hass)
    await _setup_entry(hass, entry)

    coordinator = hass.data[DOMAIN][entry.entry_id]
    coordinator.async_set_relay = AsyncMock()

    await hass.services.async_call(
        "switch",
        "turn_off",
        {"entity_id": f"switch.{NAME.lower().replace(' ', '_')}"},
        blocking=True,
    )
    coordinator.async_set_relay.assert_awaited_once_with(False)


async def test_power_sensor_value(hass):
    """Power sensor entity returns the value from coordinator data."""
    entry = _make_entry(hass)
    await _setup_entry(hass, entry)

    state = hass.states.get(f"sensor.{NAME.lower().replace(' ', '_')}_power")
    assert state is not None
    assert float(state.state) == pytest.approx(25.0)
    assert state.attributes["unit_of_measurement"] == "W"


async def test_unload_entry(hass):
    """Config entry unloads cleanly."""
    entry = _make_entry(hass)
    await _setup_entry(hass, entry)

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.entry_id not in hass.data.get(DOMAIN, {})
