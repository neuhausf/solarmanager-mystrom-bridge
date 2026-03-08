"""Shared test fixtures for SolarManager MyStrom Bridge tests."""
from __future__ import annotations

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.solarmanager_mystrom_bridge.const import DOMAIN

MOCK_HOST = "192.168.1.201"
MOCK_NAME = "Virtual Switch 1"
MOCK_REPORT = {"power": 12.5, "relay": True}


# Enable custom integrations for all tests in this package.
@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Automatically enable loading of custom integrations."""


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title=MOCK_NAME,
        data={
            "host": MOCK_HOST,
            "name": MOCK_NAME,
            "scan_interval": 5,
        },
        unique_id=MOCK_HOST.lower(),
    )
