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


async def test_relay_change_turns_off_controlled_entity(hass):
    """When relay changes True→False, homeassistant.turn_off is called on controlled entity."""
    entry = _make_entry(hass, controlled_entity_id="switch.living_room")

    # Register a dummy switch entity so HA won't reject the service call.
    hass.states.async_set("switch.living_room", "on")

    calls = []

    async def _mock_service(call):
        calls.append(call)

    hass.services.async_register("homeassistant", "turn_off", _mock_service)
    hass.services.async_register("homeassistant", "turn_on", _mock_service)

    # Set up with relay=True (initial state).
    with patch(
        "custom_components.solarmanager_mystrom_bridge.coordinator."
        "MyStromBridgeCoordinator._async_update_data",
        return_value={"power": 25.0, "relay": True},
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    # Simulate virtual device turning off (relay=False) on next poll.
    coordinator = hass.data[DOMAIN][entry.entry_id]
    coordinator.data = {"power": 0.0, "relay": False}
    coordinator.async_set_updated_data(coordinator.data)
    await hass.async_block_till_done()

    assert any(
        c.domain == "homeassistant" and c.service == "turn_off"
        and c.data.get("entity_id") == "switch.living_room"
        for c in calls
    ), "Expected homeassistant.turn_off to be called on switch.living_room"


async def test_relay_change_turns_on_controlled_entity(hass):
    """When relay changes False→True, homeassistant.turn_on is called on controlled entity."""
    entry = _make_entry(hass, controlled_entity_id="switch.living_room")

    hass.states.async_set("switch.living_room", "off")

    calls = []

    async def _mock_service(call):
        calls.append(call)

    hass.services.async_register("homeassistant", "turn_on", _mock_service)
    hass.services.async_register("homeassistant", "turn_off", _mock_service)

    # Set up with relay=False (initial state).
    with patch(
        "custom_components.solarmanager_mystrom_bridge.coordinator."
        "MyStromBridgeCoordinator._async_update_data",
        return_value={"power": 0.0, "relay": False},
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    # Simulate virtual device turning on (relay=True) on next poll.
    coordinator = hass.data[DOMAIN][entry.entry_id]
    coordinator.async_set_updated_data({"power": 100.0, "relay": True})
    await hass.async_block_till_done()

    assert any(
        c.domain == "homeassistant" and c.service == "turn_on"
        and c.data.get("entity_id") == "switch.living_room"
        for c in calls
    ), "Expected homeassistant.turn_on to be called on switch.living_room"


async def test_no_relay_sync_without_controlled_entity(hass):
    """No homeassistant service call is made if no controlled_entity_id is configured."""
    entry = _make_entry(hass)  # no controlled_entity_id

    calls = []

    async def _mock_service(call):
        calls.append(call)

    hass.services.async_register("homeassistant", "turn_off", _mock_service)
    hass.services.async_register("homeassistant", "turn_on", _mock_service)

    with patch(
        "custom_components.solarmanager_mystrom_bridge.coordinator."
        "MyStromBridgeCoordinator._async_update_data",
        return_value={"power": 25.0, "relay": True},
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    coordinator = hass.data[DOMAIN][entry.entry_id]
    coordinator.async_set_updated_data({"power": 0.0, "relay": False})
    await hass.async_block_till_done()

    assert calls == [], "Expected no homeassistant service calls without controlled entity"


async def test_no_spurious_call_on_startup(hass):
    """No homeassistant service call is made on first coordinator data (startup)."""
    entry = _make_entry(hass, controlled_entity_id="switch.living_room")

    hass.states.async_set("switch.living_room", "on")

    calls = []

    async def _mock_service(call):
        calls.append(call)

    hass.services.async_register("homeassistant", "turn_on", _mock_service)
    hass.services.async_register("homeassistant", "turn_off", _mock_service)

    with patch(
        "custom_components.solarmanager_mystrom_bridge.coordinator."
        "MyStromBridgeCoordinator._async_update_data",
        return_value={"power": 25.0, "relay": True},
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    # No state change – relay stays True on the second poll.
    coordinator = hass.data[DOMAIN][entry.entry_id]
    coordinator.async_set_updated_data({"power": 30.0, "relay": True})
    await hass.async_block_till_done()

    assert calls == [], "Expected no service call when relay did not change"
    """Config entry unloads cleanly."""
    entry = _make_entry(hass)
    await _setup_entry(hass, entry)

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.entry_id not in hass.data.get(DOMAIN, {})
