"""Calendar platform: one entity exposing all upcoming pickups."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import TommeplanConfigEntry, TommeplanCoordinator, TommeplanData

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TommeplanConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([TommeplanCalendar(entry.runtime_data, entry)])


class TommeplanCalendar(CoordinatorEntity[TommeplanCoordinator], CalendarEntity):
    """A single calendar with all pickup events for a property."""

    _attr_has_entity_name = True
    _attr_name = None  # use device name as entity name
    _attr_icon = "mdi:trash-can-outline"

    def __init__(
        self, coordinator: TommeplanCoordinator, entry: TommeplanConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_calendar"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Norconsult Digital",
            model=coordinator.kommune_name,
        )

    @property
    def event(self) -> CalendarEvent | None:
        """The next upcoming pickup, used as the entity state."""
        data: TommeplanData | None = self.coordinator.data
        if data is None:
            return None
        today = dt_util.now().date()
        for d, frac in data.pickups:
            if d >= today:
                return _event(d, frac)
        return None

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        data: TommeplanData | None = self.coordinator.data
        if data is None:
            return []
        # end_date is exclusive — compare against the day before midnight.
        start = start_date.date()
        end = end_date.date()
        return [
            _event(d, frac)
            for d, frac in data.pickups
            if start <= d < end
        ]


def _event(d: date, fraksjon: str) -> CalendarEvent:
    """Pickups are all-day events. HA expects exclusive end, so end = d + 1 day."""
    return CalendarEvent(
        start=d,
        end=d + timedelta(days=1),
        summary=fraksjon,
        description=f"Tømming av {fraksjon}",
    )
