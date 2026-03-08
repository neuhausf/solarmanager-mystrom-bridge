"""The SolarManager MyStrom Bridge integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_SCAN_INTERVAL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_state_change_event

from .const import CONF_POWER_ENTITY_ID, DEFAULT_SCAN_INTERVAL, DOMAIN
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
