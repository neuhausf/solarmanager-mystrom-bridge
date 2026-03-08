"""Switch platform for the SolarManager MyStrom Bridge integration."""
from __future__ import annotations

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MyStromBridgeCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the relay switch entity."""
    coordinator: MyStromBridgeCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MyStromRelaySwitch(coordinator, entry)])


class MyStromRelaySwitch(CoordinatorEntity[MyStromBridgeCoordinator], SwitchEntity):
    """Switch entity representing the relay of a virtual MyStrom device."""

    _attr_device_class = SwitchDeviceClass.OUTLET
    _attr_has_entity_name = True
    _attr_name = None  # The device name is used as the entity name

    def __init__(
        self,
        coordinator: MyStromBridgeCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialise the relay switch."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_relay"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.title,
            manufacturer="Virtual MyStrom",
            model="MyStrom Energy Control Switch",
            configuration_url=f"http://{self._entry.data['host']}",
        )

    @property
    def is_on(self) -> bool | None:
        """Return True if the relay is on."""
        if self.coordinator.data is None:
            return None
        relay = self.coordinator.data.get("relay")
        if relay is None:
            return None
        return bool(relay)

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the relay on."""
        await self.coordinator.async_set_relay(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the relay off."""
        await self.coordinator.async_set_relay(False)
        await self.coordinator.async_request_refresh()
