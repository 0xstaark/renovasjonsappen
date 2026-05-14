"""Tests for the Tømmeplan config flow."""
from __future__ import annotations

from unittest.mock import AsyncMock

import aiohttp
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tommeplan.api import TommeplanApiError
from custom_components.tommeplan.const import (
    CONF_ADRESSE,
    CONF_EIENDOM_ID,
    CONF_KOMMUNE,
    DOMAIN,
)

EIENDOM_HIT = {
    "id": "abc-123",
    "adresse": "Eksempelveien 1",
    "gNr": "12",
    "bNr": "34",
    "fNr": "0",
    "sNr": "0",
    "kommuneNr": "1121",
    "eier": "Ola Nordmann",  # should NOT end up in entry data
}


async def _start(hass: HomeAssistant) -> dict:
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )


async def test_full_flow(
    hass: HomeAssistant, mock_search_eiendommer: AsyncMock
) -> None:
    mock_search_eiendommer.return_value = [EIENDOM_HIT]

    result = await _start(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_KOMMUNE: "time", CONF_ADRESSE: "Eksempelveien 1"},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "pick"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_EIENDOM_ID: "abc-123"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        CONF_KOMMUNE: "time",
        CONF_EIENDOM_ID: "abc-123",
        CONF_ADRESSE: "Eksempelveien 1",
    }
    # Owner field from search must not be persisted.
    assert "eier" not in result["data"]


async def test_no_results(
    hass: HomeAssistant, mock_search_eiendommer: AsyncMock
) -> None:
    mock_search_eiendommer.return_value = []

    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_KOMMUNE: "time", CONF_ADRESSE: "Nowhere 99"},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_ADRESSE: "no_results"}


async def test_wrong_kommune_filtered(
    hass: HomeAssistant, mock_search_eiendommer: AsyncMock
) -> None:
    """Hits in other kommuner are filtered out by kommuneNr."""
    mock_search_eiendommer.return_value = [{**EIENDOM_HIT, "kommuneNr": "9999"}]

    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_KOMMUNE: "time", CONF_ADRESSE: "Eksempelveien 1"},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_ADRESSE: "no_results"}


async def test_api_error_shows_cannot_connect(
    hass: HomeAssistant, mock_search_eiendommer: AsyncMock
) -> None:
    mock_search_eiendommer.side_effect = TommeplanApiError("boom")

    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_KOMMUNE: "time", CONF_ADRESSE: "Eksempelveien 1"},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_network_error_shows_cannot_connect(
    hass: HomeAssistant, mock_search_eiendommer: AsyncMock
) -> None:
    mock_search_eiendommer.side_effect = aiohttp.ClientError("offline")

    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_KOMMUNE: "time", CONF_ADRESSE: "Eksempelveien 1"},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_unexpected_error_shows_unknown(
    hass: HomeAssistant, mock_search_eiendommer: AsyncMock
) -> None:
    mock_search_eiendommer.side_effect = RuntimeError("surprise")

    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_KOMMUNE: "time", CONF_ADRESSE: "Eksempelveien 1"},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "unknown"}


async def test_duplicate_aborts(
    hass: HomeAssistant, mock_search_eiendommer: AsyncMock
) -> None:
    MockConfigEntry(
        domain=DOMAIN,
        unique_id="time:abc-123",
        data={
            CONF_KOMMUNE: "time",
            CONF_EIENDOM_ID: "abc-123",
            CONF_ADRESSE: "Eksempelveien 1",
        },
    ).add_to_hass(hass)
    mock_search_eiendommer.return_value = [EIENDOM_HIT]

    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_KOMMUNE: "time", CONF_ADRESSE: "Eksempelveien 1"},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_EIENDOM_ID: "abc-123"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
