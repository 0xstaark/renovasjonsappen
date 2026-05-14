"""Tests for setup/unload of the Tømmeplan integration."""
from __future__ import annotations

from unittest.mock import AsyncMock

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tommeplan.const import (
    CONF_ADRESSE,
    CONF_EIENDOM_ID,
    CONF_KOMMUNE,
    DOMAIN,
)

SAMPLE_TOMMINGER = [
    {"dato": "2026-05-18T00:00:00", "fraksjon": "Restavfall"},
    {"dato": "2026-05-25T00:00:00", "fraksjon": "Matavfall"},
    {"dato": "2026-06-01T00:00:00", "fraksjon": "Restavfall"},
]


def _entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id="time:abc-123",
        title="Time kommune – Eksempelveien 1",
        data={
            CONF_KOMMUNE: "time",
            CONF_EIENDOM_ID: "abc-123",
            CONF_ADRESSE: "Eksempelveien 1",
        },
    )


async def test_setup_and_unload(
    hass: HomeAssistant, mock_get_tomminger: AsyncMock
) -> None:
    mock_get_tomminger.return_value = SAMPLE_TOMMINGER

    entry = _entry()
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED

    sensors = [
        s for s in hass.states.async_all() if s.entity_id.startswith("sensor.")
    ]
    calendars = [
        s for s in hass.states.async_all() if s.entity_id.startswith("calendar.")
    ]
    # One sensor per distinct fraksjon (Restavfall, Matavfall) plus one calendar.
    assert len(sensors) == 2
    assert len(calendars) == 1

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_setup_retries_on_api_error(
    hass: HomeAssistant, mock_get_tomminger: AsyncMock
) -> None:
    """A failed first refresh should leave the entry in SETUP_RETRY."""
    from custom_components.tommeplan.api import TommeplanApiError

    mock_get_tomminger.side_effect = TommeplanApiError("backend down")

    entry = _entry()
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_RETRY
