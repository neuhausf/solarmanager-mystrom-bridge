"""Sensor platform for the SolarManager MyStrom Bridge integration."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower
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
    """Set up the power sensor entity."""
    coordinator: MyStromBridgeCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MyStromPowerSensor(coordinator, entry)])


class MyStromPowerSensor(CoordinatorEntity[MyStromBridgeCoordinator], SensorEntity):
    """Sensor entity representing the current power of a virtual MyStrom device."""

    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_has_entity_name = True
    _attr_translation_key = "power"

    def __init__(
        self,
        coordinator: MyStromBridgeCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialise the power sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_power"

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
    def native_value(self) -> float | None:
        """Return the current power reading from the device report."""
        if self.coordinator.data is None:
            return None
        power = self.coordinator.data.get("power")
        if power is None:
            return None
        try:
            return float(power)
        except (ValueError, TypeError):
            return None
