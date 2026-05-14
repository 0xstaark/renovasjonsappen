"""Sensor platform: one sensor per fraksjon, state = next pickup date."""
from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN, ICON_MAP
from .coordinator import TommeplanConfigEntry, TommeplanCoordinator, TommeplanData

PARALLEL_UPDATES = 0

# Translation keys we ship in strings.json / translations/*.json. Derived from
# ICON_MAP so the two lists can't drift.
_KNOWN_TRANSLATION_KEYS: set[str] = {
    "".join(c for c in k if c.isalnum()).lower() for k in ICON_MAP
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TommeplanConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create one sensor per fraksjon that appears in the coordinator data."""
    coordinator = entry.runtime_data
    known: set[str] = set()

    @callback
    def _add_new_sensors() -> None:
        data: TommeplanData | None = coordinator.data
        if data is None:
            return
        new_fracs = [f for f in data.pickups_by_fraksjon if f not in known]
        if new_fracs:
            known.update(new_fracs)
            async_add_entities(
                TommeplanFraksjonSensor(coordinator, entry, f) for f in new_fracs
            )

    _add_new_sensors()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_sensors))


class TommeplanFraksjonSensor(CoordinatorEntity[TommeplanCoordinator], SensorEntity):
    """Next pickup date for a single fraksjon (e.g., 'Restavfall')."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(
        self,
        coordinator: TommeplanCoordinator,
        entry: TommeplanConfigEntry,
        fraksjon: str,
    ) -> None:
        super().__init__(coordinator)
        self._fraksjon = fraksjon
        slug = _normalize(fraksjon)
        self._attr_unique_id = f"{entry.entry_id}_{slug}"
        if slug in _KNOWN_TRANSLATION_KEYS:
            self._attr_translation_key = slug
        else:
            self._attr_name = fraksjon
        self._attr_icon = _icon_for(fraksjon)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Norconsult Digital",
            model=coordinator.kommune_name,
        )

    @property
    def native_value(self) -> datetime | None:
        data: TommeplanData | None = self.coordinator.data
        if data is None:
            return None
        nxt = data.next_pickup(self._fraksjon, dt_util.now().date())
        if nxt is None:
            return None
        # Pickup is an all-day local event; anchor at midnight in the HA timezone.
        return dt_util.start_of_local_day(nxt)

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        data = self.coordinator.data
        if data is None:
            return {"fraksjon": self._fraksjon, "days_until": None, "all_upcoming": []}
        today = dt_util.now().date()
        upcoming = [d for d in data.pickups_by_fraksjon.get(self._fraksjon, []) if d >= today]
        nxt = upcoming[0] if upcoming else None
        return {
            "fraksjon": self._fraksjon,
            "days_until": (nxt - today).days if nxt else None,
            "all_upcoming": [d.isoformat() for d in upcoming],
        }


def _icon_for(fraksjon: str) -> str:
    """Look up icon by collapsing whitespace/punctuation and ignoring case."""
    key = _normalize(fraksjon)
    for k, icon in ICON_MAP.items():
        if k.lower() == key:
            return icon
    return "mdi:trash-can"


def _normalize(s: str) -> str:
    """Lowercase, alphanumeric-only — used for translation keys and icon lookup."""
    return "".join(c for c in s if c.isalnum()).lower()
