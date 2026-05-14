"""Shared fixtures for Tømmeplan tests."""
from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> None:
    """Enable the tommeplan custom integration for all tests."""
    return enable_custom_integrations


@pytest.fixture
def mock_search_eiendommer() -> Generator[AsyncMock, None, None]:
    """Mock the address-search API call used by the config flow."""
    with patch(
        "custom_components.tommeplan.config_flow.TommeplanClient.search_eiendommer",
        new_callable=AsyncMock,
    ) as mock:
        yield mock


@pytest.fixture
def mock_get_tomminger() -> Generator[AsyncMock, None, None]:
    """Mock the schedule-fetch API call used by the coordinator."""
    with patch(
        "custom_components.tommeplan.coordinator.TommeplanClient.get_tomminger",
        new_callable=AsyncMock,
    ) as mock:
        yield mock
