"""Tømmeplan integration — Home Assistant entry point."""
from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import TommeplanConfigEntry, TommeplanCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.CALENDAR]


async def async_setup_entry(
    hass: HomeAssistant, entry: TommeplanConfigEntry
) -> bool:
    coordinator = TommeplanCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: TommeplanConfigEntry
) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
