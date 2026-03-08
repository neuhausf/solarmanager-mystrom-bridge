"""Config flow for the SolarManager MyStrom Bridge integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
)

from .const import CONF_CONTROLLED_ENTITY_ID, CONF_POWER_ENTITY_ID, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def _validate_host(session: aiohttp.ClientSession, host: str) -> None:
    """Try connecting to the virtual device to validate the host."""
    url = f"http://{host}/report"
    async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
        resp.raise_for_status()


class SolarManagerMyStromBridgeConfigFlow(
    config_entries.ConfigFlow, domain=DOMAIN
):
    """Handle a config flow for SolarManager MyStrom Bridge."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize flow."""
        self._user_input: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            session = async_get_clientsession(self.hass)
            try:
                await _validate_host(session, host)
            except aiohttp.ClientError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error connecting to %s", host)
                errors["base"] = "unknown"
            else:
                self._user_input = {**user_input, CONF_HOST: host}
                return await self.async_step_power()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME): TextSelector(),
                    vol.Required(CONF_HOST): TextSelector(),
                    vol.Optional(
                        CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=1,
                            max=3600,
                            step=1,
                            mode=NumberSelectorMode.BOX,
                        )
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_power(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle optional power-source and controlled-entity configuration step."""
        if user_input is not None:
            data = dict(self._user_input)
            power_entity_id = (user_input.get(CONF_POWER_ENTITY_ID) or "").strip()
            if power_entity_id:
                data[CONF_POWER_ENTITY_ID] = power_entity_id

            controlled_entity_id = (
                user_input.get(CONF_CONTROLLED_ENTITY_ID) or ""
            ).strip()
            if controlled_entity_id:
                data[CONF_CONTROLLED_ENTITY_ID] = controlled_entity_id

            await self.async_set_unique_id(data[CONF_HOST].lower())
            self._abort_if_unique_id_configured()

            return self.async_create_entry(title=data[CONF_NAME], data=data)

        return self.async_show_form(
            step_id="power",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_CONTROLLED_ENTITY_ID): EntitySelector(
                        EntitySelectorConfig(
                            domain=["switch", "input_boolean", "light"]
                        )
                    ),
                    vol.Optional(CONF_POWER_ENTITY_ID): EntitySelector(
                        EntitySelectorConfig(domain=["sensor"])
                    ),
                }
            ),
            description_placeholders={
                "name": self._user_input.get(CONF_NAME, ""),
                "host": self._user_input.get(CONF_HOST, ""),
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> OptionsFlowHandler:
        """Return the options flow handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for SolarManager MyStrom Bridge."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle options."""
        if user_input is not None:
            # Strip empty entities
            if not (user_input.get(CONF_POWER_ENTITY_ID) or "").strip():
                user_input.pop(CONF_POWER_ENTITY_ID, None)
            if not (user_input.get(CONF_CONTROLLED_ENTITY_ID) or "").strip():
                user_input.pop(CONF_CONTROLLED_ENTITY_ID, None)
            return self.async_create_entry(title="", data=user_input)

        current_scan_interval = int(
            self._config_entry.options.get(
                CONF_SCAN_INTERVAL,
                self._config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            )
        )
        current_power_entity = self._config_entry.options.get(
            CONF_POWER_ENTITY_ID,
            self._config_entry.data.get(CONF_POWER_ENTITY_ID, ""),
        )
        current_controlled_entity = self._config_entry.options.get(
            CONF_CONTROLLED_ENTITY_ID,
            self._config_entry.data.get(CONF_CONTROLLED_ENTITY_ID, ""),
        )

        controlled_selector = EntitySelector(
            EntitySelectorConfig(domain=["switch", "input_boolean", "light"])
        )
        power_selector = EntitySelector(EntitySelectorConfig(domain=["sensor"]))

        schema: dict = {
            vol.Optional(
                CONF_SCAN_INTERVAL, default=current_scan_interval
            ): NumberSelector(
                NumberSelectorConfig(
                    min=1,
                    max=3600,
                    step=1,
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(
                CONF_CONTROLLED_ENTITY_ID,
                **({"default": current_controlled_entity} if current_controlled_entity else {}),
            ): controlled_selector,
            vol.Optional(
                CONF_POWER_ENTITY_ID,
                **({"default": current_power_entity} if current_power_entity else {}),
            ): power_selector,
        }

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema),
        )
