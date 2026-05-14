"""DataUpdateCoordinator for the Tømmeplan integration."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import TommeplanApiError, TommeplanClient
from .const import (
    CONF_EIENDOM_ID,
    CONF_KOMMUNE,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    KOMMUNER,
    SCHEDULE_LOOKAHEAD_DAYS,
)

_LOGGER = logging.getLogger(__name__)

type TommeplanConfigEntry = ConfigEntry["TommeplanCoordinator"]


@dataclass
class TommeplanData:
    """Coordinator output: schedule grouped by fraksjon plus a flat list."""

    eiendom_id: str
    kommune: str
    pickups_by_fraksjon: dict[str, list[date]] = field(default_factory=dict)
    pickups: list[tuple[date, str]] = field(default_factory=list)

    def next_pickup(self, fraksjon: str, today: date) -> date | None:
        candidates = [
            d for d in self.pickups_by_fraksjon.get(fraksjon, []) if d >= today
        ]
        return min(candidates) if candidates else None


class TommeplanCoordinator(DataUpdateCoordinator[TommeplanData]):
    """Fetches the full year of pickup dates once per day."""

    def __init__(self, hass: HomeAssistant, entry: TommeplanConfigEntry) -> None:
        kommune = entry.data[CONF_KOMMUNE]
        eiendom_id = entry.data[CONF_EIENDOM_ID]
        cfg = KOMMUNER[kommune]

        self.eiendom_id = eiendom_id
        self.kommune = kommune
        self.kommune_name = cfg["name"]
        self.host = cfg["host"]
        self._client = TommeplanClient(
            session=async_get_clientsession(hass),
            host=self.host,
            applikasjons_id=cfg["applikasjonsId"],
            oppdragsgiver_id=cfg["oppdragsgiverId"],
        )

        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}:{kommune}:{eiendom_id[:8]}",
            update_interval=DEFAULT_SCAN_INTERVAL,
        )

    async def _async_update_data(self) -> TommeplanData:
        today = dt_util.now().date()
        end = today + timedelta(days=SCHEDULE_LOOKAHEAD_DAYS)
        try:
            raw = await self._client.get_tomminger(self.eiendom_id, today, end)
        except TommeplanApiError as err:
            raise UpdateFailed(str(err)) from err

        if not isinstance(raw, list):
            raise UpdateFailed(
                f"unexpected response shape: {type(raw).__name__}"
            )

        by_frac: dict[str, list[date]] = {}
        flat: list[tuple[date, str]] = []
        for ev in raw:
            d = _parse_dato(ev.get("dato"))
            frac = ev.get("fraksjon")
            if d is None or not frac:
                continue
            by_frac.setdefault(frac, []).append(d)
            flat.append((d, frac))

        for k in by_frac:
            by_frac[k].sort()
        flat.sort()

        return TommeplanData(
            eiendom_id=self.eiendom_id,
            kommune=self.kommune,
            pickups_by_fraksjon=by_frac,
            pickups=flat,
        )


def _parse_dato(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    # API returns e.g. "2026-05-18T00:00:00"
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None
