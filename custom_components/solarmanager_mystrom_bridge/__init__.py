"""The SolarManager MyStrom Bridge integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_SCAN_INTERVAL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_state_change_event

from .const import CONF_CONTROLLED_ENTITY_ID, CONF_POWER_ENTITY_ID, CONF_TEMPERATURE_ENTITY_ID, DEFAULT_SCAN_INTERVAL, DOMAIN
from .coordinator import MyStromBridgeCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SWITCH, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SolarManager MyStrom Bridge from a config entry."""
    host = entry.data[CONF_HOST]
    scan_interval = int(
        entry.options.get(
            CONF_SCAN_INTERVAL,
            entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
    )

    session = async_get_clientsession(hass)
    coordinator = MyStromBridgeCoordinator(hass, session, host, scan_interval)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Forward power readings from a HA entity to the virtual device's /power endpoint.
    power_entity_id = entry.options.get(
        CONF_POWER_ENTITY_ID,
        entry.data.get(CONF_POWER_ENTITY_ID),
    )
    if power_entity_id:
        _LOGGER.debug(
            "Tracking power entity %s for device %s", power_entity_id, host
        )

        async def _on_power_state_changed(event):
            new_state = event.data.get("new_state")
            if new_state is None or new_state.state in (
                None,
                "unavailable",
                "unknown",
            ):
                return
            try:
                power = float(new_state.state)
            except (ValueError, TypeError):
                _LOGGER.warning(
                    "Cannot parse power value '%s' from entity %s",
                    new_state.state,
                    power_entity_id,
                )
                return
            await coordinator.async_set_power(power)

        entry.async_on_unload(
            async_track_state_change_event(
                hass, [power_entity_id], _on_power_state_changed
            )
        )

    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    # Forward temperature readings from a HA entity to the virtual device's /temperature endpoint.
    temperature_entity_id = entry.options.get(
        CONF_TEMPERATURE_ENTITY_ID,
        entry.data.get(CONF_TEMPERATURE_ENTITY_ID),
    )
    if temperature_entity_id:
        _LOGGER.debug(
            "Tracking temperature entity %s for device %s", temperature_entity_id, host
        )

        async def _on_temperature_state_changed(event):
            new_state = event.data.get("new_state")
            if new_state is None or new_state.state in (
                None,
                "unavailable",
                "unknown",
            ):
                return
            try:
                temperature = float(new_state.state)
            except (ValueError, TypeError):
                _LOGGER.warning(
                    "Cannot parse temperature value '%s' from entity %s",
                    new_state.state,
                    temperature_entity_id,
                )
                return
            await coordinator.async_set_temperature(temperature)

        entry.async_on_unload(
            async_track_state_change_event(
                hass, [temperature_entity_id], _on_temperature_state_changed
            )
        )

    # Synchronize a configured HA entity when the virtual device relay state changes.
    controlled_entity_id = entry.options.get(
        CONF_CONTROLLED_ENTITY_ID,
        entry.data.get(CONF_CONTROLLED_ENTITY_ID),
    )
    if controlled_entity_id:
        _LOGGER.debug(
            "Will synchronize relay state to entity %s for device %s",
            controlled_entity_id,
            host,
        )
        # Seed with current relay state so startup does not trigger a spurious call.
        _previous_relay: bool | None = (
            bool(coordinator.data.get("relay"))
            if coordinator.data and coordinator.data.get("relay") is not None
            else None
        )

        async def _on_relay_changed() -> None:
            nonlocal _previous_relay
            if coordinator.data is None:
                return
            relay = coordinator.data.get("relay")
            if relay is None:
                return
            relay_on = bool(relay)
            if relay_on == _previous_relay:
                return
            _previous_relay = relay_on
            _LOGGER.debug(
                "Relay on %s changed to %s – calling homeassistant.%s on %s",
                host,
                relay_on,
                "turn_on" if relay_on else "turn_off",
                controlled_entity_id,
            )
            await hass.services.async_call(
                "homeassistant",
                "turn_on" if relay_on else "turn_off",
                {"entity_id": controlled_entity_id},
                blocking=False,
            )

        entry.async_on_unload(
            coordinator.async_add_listener(
                lambda: hass.async_create_task(_on_relay_changed())
            )
        )

        # Synchronize the virtual device relay when the controlled HA entity changes.
        async def _on_controlled_entity_changed(event) -> None:
            nonlocal _previous_relay
            new_state = event.data.get("new_state")
            if new_state is None or new_state.state in (
                None,
                "unavailable",
                "unknown",
            ):
                return
            relay_on = new_state.state not in ("off", "false", "0")
            # Skip if this matches the state we already set (prevents feedback loop).
            if relay_on == _previous_relay:
                return
            # Update _previous_relay BEFORE the await so that any concurrent listener
            # invocation (asyncio is cooperative; no actual parallelism here) sees the
            # new value and skips the redundant relay call.
            _previous_relay = relay_on
            _LOGGER.debug(
                "Controlled entity %s changed to %s – setting relay on %s to %s",
                controlled_entity_id,
                new_state.state,
                host,
                relay_on,
            )
            await coordinator.async_set_relay(relay_on)

        entry.async_on_unload(
            async_track_state_change_event(
                hass, [controlled_entity_id], _on_controlled_entity_changed
            )
        )

    return True


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
