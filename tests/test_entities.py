"""Tests for switch and sensor entities."""
from __future__ import annotations

import logging
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


async def test_unload_entry(hass):
    """Config entry unloads cleanly."""
    entry = _make_entry(hass)
    await _setup_entry(hass, entry)

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.entry_id not in hass.data.get(DOMAIN, {})


async def test_controlled_entity_on_calls_relay_on(hass):
    """When the controlled HA entity turns on, async_set_relay(True) is called."""
    entry = _make_entry(hass, controlled_entity_id="switch.living_room")

    # Start with relay=False so the HA entity turning on represents a change.
    hass.states.async_set("switch.living_room", "off")

    with patch(
        "custom_components.solarmanager_mystrom_bridge.coordinator."
        "MyStromBridgeCoordinator._async_update_data",
        return_value={"power": 0.0, "relay": False},
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    coordinator = hass.data[DOMAIN][entry.entry_id]
    coordinator.async_set_relay = AsyncMock()

    # Simulate user turning on the entity in HA.
    hass.states.async_set("switch.living_room", "on")
    await hass.async_block_till_done()

    coordinator.async_set_relay.assert_awaited_once_with(True)


async def test_controlled_entity_off_calls_relay_off(hass):
    """When the controlled HA entity turns off, async_set_relay(False) is called."""
    entry = _make_entry(hass, controlled_entity_id="switch.living_room")

    hass.states.async_set("switch.living_room", "on")

    with patch(
        "custom_components.solarmanager_mystrom_bridge.coordinator."
        "MyStromBridgeCoordinator._async_update_data",
        return_value={"power": 25.0, "relay": True},
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    coordinator = hass.data[DOMAIN][entry.entry_id]
    coordinator.async_set_relay = AsyncMock()

    # Simulate user turning off the entity in HA.
    hass.states.async_set("switch.living_room", "off")
    await hass.async_block_till_done()

    coordinator.async_set_relay.assert_awaited_once_with(False)


async def test_no_relay_api_loop_on_mystrom_initiated_change(hass):
    """When myStrom changes relay, the resulting HA state change must NOT call relay API again."""
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

    coordinator = hass.data[DOMAIN][entry.entry_id]
    coordinator.async_set_relay = AsyncMock()

    # myStrom turns relay off → integration calls homeassistant.turn_off → entity turns off.
    coordinator.async_set_updated_data({"power": 0.0, "relay": False})
    await hass.async_block_till_done()

    # Simulate the HA entity responding to that service call.
    hass.states.async_set("switch.living_room", "off")
    await hass.async_block_till_done()

    # The relay API must NOT be called because the change was initiated by myStrom.
    coordinator.async_set_relay.assert_not_called()


async def test_no_ha_to_mystrom_sync_without_controlled_entity(hass):
    """State changes of unrelated entities must not call relay API."""
    entry = _make_entry(hass)  # no controlled_entity_id

    await _setup_entry(hass, entry)

    coordinator = hass.data[DOMAIN][entry.entry_id]
    coordinator.async_set_relay = AsyncMock()

    hass.states.async_set("switch.some_other_entity", "on")
    await hass.async_block_till_done()

    coordinator.async_set_relay.assert_not_called()


async def test_temperature_entity_forwards_to_coordinator(hass):
    """When temperature entity changes, async_set_temperature is called with the new value."""
    entry = _make_entry(hass, temperature_entity_id="sensor.room_temp")

    hass.states.async_set("sensor.room_temp", "20.0")

    await _setup_entry(hass, entry)

    coordinator = hass.data[DOMAIN][entry.entry_id]
    coordinator.async_set_temperature = AsyncMock()

    hass.states.async_set("sensor.room_temp", "21.5")
    await hass.async_block_till_done()

    coordinator.async_set_temperature.assert_awaited_once_with(21.5)


async def test_no_temperature_forward_without_temperature_entity(hass):
    """async_set_temperature is not called when no temperature_entity_id is configured."""
    entry = _make_entry(hass)  # no temperature_entity_id

    await _setup_entry(hass, entry)

    coordinator = hass.data[DOMAIN][entry.entry_id]
    coordinator.async_set_temperature = AsyncMock()

    hass.states.async_set("sensor.room_temp", "21.5")
    await hass.async_block_till_done()

    coordinator.async_set_temperature.assert_not_called()


async def test_temperature_entity_invalid_value_logs_warning(hass, caplog):
    """When temperature entity has an unparseable value, a warning is logged and no API call is made."""
    entry = _make_entry(hass, temperature_entity_id="sensor.room_temp")

    hass.states.async_set("sensor.room_temp", "20.0")

    await _setup_entry(hass, entry)

    coordinator = hass.data[DOMAIN][entry.entry_id]
    coordinator.async_set_temperature = AsyncMock()

    with caplog.at_level(logging.WARNING):
        hass.states.async_set("sensor.room_temp", "not_a_number")
        await hass.async_block_till_done()

    coordinator.async_set_temperature.assert_not_called()
    assert "Cannot parse temperature value" in caplog.text


async def test_power_entity_initial_push_on_load(hass):
    """When the power entity has a valid state at load time, async_set_power is called immediately."""
    entry = _make_entry(hass, power_entity_id="sensor.solar_power")

    hass.states.async_set("sensor.solar_power", "42.0")

    with patch(
        "custom_components.solarmanager_mystrom_bridge.coordinator."
        "MyStromBridgeCoordinator._async_update_data",
        return_value={"power": 25.0, "relay": True},
    ), patch(
        "custom_components.solarmanager_mystrom_bridge.coordinator."
        "MyStromBridgeCoordinator.async_set_power",
        new_callable=AsyncMock,
    ) as mock_set_power:
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    mock_set_power.assert_awaited_with(42.0)


async def test_temperature_entity_initial_push_on_load(hass):
    """When the temperature entity has a valid state at load time, async_set_temperature is called immediately."""
    entry = _make_entry(hass, temperature_entity_id="sensor.room_temp")

    hass.states.async_set("sensor.room_temp", "19.5")

    with patch(
        "custom_components.solarmanager_mystrom_bridge.coordinator."
        "MyStromBridgeCoordinator._async_update_data",
        return_value={"power": 25.0, "relay": True},
    ), patch(
        "custom_components.solarmanager_mystrom_bridge.coordinator."
        "MyStromBridgeCoordinator.async_set_temperature",
        new_callable=AsyncMock,
    ) as mock_set_temperature:
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    mock_set_temperature.assert_awaited_with(19.5)


async def test_power_entity_no_initial_push_when_unavailable(hass):
    """When the power entity is unavailable at load time, async_set_power is NOT called."""
    entry = _make_entry(hass, power_entity_id="sensor.solar_power")

    hass.states.async_set("sensor.solar_power", "unavailable")

    with patch(
        "custom_components.solarmanager_mystrom_bridge.coordinator."
        "MyStromBridgeCoordinator._async_update_data",
        return_value={"power": 25.0, "relay": True},
    ), patch(
        "custom_components.solarmanager_mystrom_bridge.coordinator."
        "MyStromBridgeCoordinator.async_set_power",
        new_callable=AsyncMock,
    ) as mock_set_power:
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    mock_set_power.assert_not_awaited()


async def test_temperature_entity_no_initial_push_when_unavailable(hass):
    """When the temperature entity is unavailable at load time, async_set_temperature is NOT called."""
    entry = _make_entry(hass, temperature_entity_id="sensor.room_temp")

    hass.states.async_set("sensor.room_temp", "unavailable")

    with patch(
        "custom_components.solarmanager_mystrom_bridge.coordinator."
        "MyStromBridgeCoordinator._async_update_data",
        return_value={"power": 25.0, "relay": True},
    ), patch(
        "custom_components.solarmanager_mystrom_bridge.coordinator."
        "MyStromBridgeCoordinator.async_set_temperature",
        new_callable=AsyncMock,
    ) as mock_set_temperature:
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    mock_set_temperature.assert_not_awaited()


async def test_power_entity_no_initial_push_when_entity_missing(hass):
    """When the power entity does not exist at load time, async_set_power is NOT called."""
    entry = _make_entry(hass, power_entity_id="sensor.solar_power")
    # Do NOT set a state for sensor.solar_power – entity does not exist yet.

    with patch(
        "custom_components.solarmanager_mystrom_bridge.coordinator."
        "MyStromBridgeCoordinator._async_update_data",
        return_value={"power": 25.0, "relay": True},
    ), patch(
        "custom_components.solarmanager_mystrom_bridge.coordinator."
        "MyStromBridgeCoordinator.async_set_power",
        new_callable=AsyncMock,
    ) as mock_set_power:
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    mock_set_power.assert_not_awaited()


async def test_power_entity_no_initial_push_invalid_value_logs_warning(hass, caplog):
    """When the power entity has an unparseable initial state, a warning is logged and no push is made."""
    entry = _make_entry(hass, power_entity_id="sensor.solar_power")

    hass.states.async_set("sensor.solar_power", "not_a_number")

    with patch(
        "custom_components.solarmanager_mystrom_bridge.coordinator."
        "MyStromBridgeCoordinator._async_update_data",
        return_value={"power": 25.0, "relay": True},
    ), patch(
        "custom_components.solarmanager_mystrom_bridge.coordinator."
        "MyStromBridgeCoordinator.async_set_power",
        new_callable=AsyncMock,
    ) as mock_set_power:
        with caplog.at_level(logging.WARNING):
            assert await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()

    mock_set_power.assert_not_awaited()
    assert "Cannot parse initial power value" in caplog.text
