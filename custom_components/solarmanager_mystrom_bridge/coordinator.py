"""DataUpdateCoordinator for the SolarManager MyStrom Bridge integration."""
from __future__ import annotations

import logging
from datetime import timedelta

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)


class MyStromBridgeCoordinator(DataUpdateCoordinator):
    """Coordinator that polls the virtual MyStrom device's /report endpoint."""

    def __init__(
        self,
        hass: HomeAssistant,
        session: aiohttp.ClientSession,
        host: str,
        scan_interval: int,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="MyStrom Bridge",
            update_interval=timedelta(seconds=scan_interval),
        )
        self.host = host
        self._base_url = f"http://{host}"
        self._session = session

    async def _async_update_data(self) -> dict:
        """Fetch data from the virtual MyStrom /report endpoint."""
        try:
            async with self._session.get(
                f"{self._base_url}/report",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                resp.raise_for_status()
                return await resp.json(content_type=None)
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error communicating with device at {self.host}: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error from device at {self.host}: {err}") from err

    async def async_set_relay(self, state: bool) -> None:
        """Set the relay state on the virtual MyStrom device."""
        state_value = 1 if state else 0
        try:
            async with self._session.get(
                f"{self._base_url}/relay",
                params={"state": state_value},
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                resp.raise_for_status()
        except aiohttp.ClientError as err:
            _LOGGER.error("Failed to set relay on %s: %s", self.host, err)

    async def async_set_power(self, power: float) -> None:
        """POST current power (W) to the virtual MyStrom /power endpoint."""
        try:
            async with self._session.post(
                f"{self._base_url}/power",
                json={"power": power},
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                resp.raise_for_status()
        except aiohttp.ClientError as err:
            _LOGGER.error("Failed to post power to %s: %s", self.host, err)
