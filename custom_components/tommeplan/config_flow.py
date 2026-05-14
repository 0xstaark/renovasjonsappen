"""Config flow for the Tømmeplan integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import TommeplanApiError, TommeplanClient
from .const import CONF_ADRESSE, CONF_EIENDOM_ID, CONF_KOMMUNE, DOMAIN, KOMMUNER

_LOGGER = logging.getLogger(__name__)


class TommeplanConfigFlow(ConfigFlow, domain=DOMAIN):
    """Two-step flow: kommune + address → pick property → save eiendomId."""

    VERSION = 1

    def __init__(self) -> None:
        self._kommune: str | None = None
        self._adresse: str | None = None
        self._matches: list[dict[str, Any]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """First step: ask for kommune and street address."""
        errors: dict[str, str] = {}

        if user_input is not None:
            kommune = user_input[CONF_KOMMUNE]
            adresse = user_input[CONF_ADRESSE].strip()
            cfg = KOMMUNER[kommune]

            try:
                client = TommeplanClient(
                    session=async_get_clientsession(self.hass),
                    host=cfg["host"],
                    applikasjons_id=cfg["applikasjonsId"],
                    oppdragsgiver_id=cfg["oppdragsgiverId"],
                )
                results = await client.search_eiendommer(adresse)
            except TommeplanApiError as err:
                _LOGGER.warning("address search failed: %s", err)
                errors["base"] = "cannot_connect"
            except aiohttp.ClientError as err:
                _LOGGER.warning("network error: %s", err)
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("unexpected error during address search")
                errors["base"] = "unknown"
            else:
                # Norconsult's /eiendommer?adresse= does not filter by
                # oppdragsgiver, so a generic street name can return hits from
                # neighbouring municipalities — guard against the wrong kommune.
                kommunenr = cfg["kommunenr"]
                results = [r for r in results if str(r.get("kommuneNr")) == kommunenr]

                if not results:
                    errors[CONF_ADRESSE] = "no_results"
                else:
                    # Strip the `eier` field — we don't want third-party owner
                    # names in entry data. See api.py.
                    self._kommune = kommune
                    self._adresse = adresse
                    self._matches = [
                        {
                            "id": r["id"],
                            "adresse": r.get("adresse", ""),
                            "gNr": r.get("gNr", ""),
                            "bNr": r.get("bNr", ""),
                            "fNr": r.get("fNr", ""),
                            "sNr": r.get("sNr", ""),
                        }
                        for r in results
                    ]
                    return await self.async_step_pick()

        schema = vol.Schema(
            {
                vol.Required(CONF_KOMMUNE, default="time"): vol.In(
                    {k: v["name"] for k, v in KOMMUNER.items()}
                ),
                vol.Required(CONF_ADRESSE): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_pick(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Second step: user picks the right property from search results."""
        assert self._kommune is not None

        if user_input is not None:
            eiendom_id = user_input[CONF_EIENDOM_ID]
            await self.async_set_unique_id(f"{self._kommune}:{eiendom_id}")
            self._abort_if_unique_id_configured()

            chosen = next(m for m in self._matches if m["id"] == eiendom_id)
            title = f"{KOMMUNER[self._kommune]['name']} – {_label(chosen)}"
            return self.async_create_entry(
                title=title,
                data={
                    CONF_KOMMUNE: self._kommune,
                    CONF_EIENDOM_ID: eiendom_id,
                    CONF_ADRESSE: chosen.get("adresse", ""),
                },
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_EIENDOM_ID): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(
                                value=m["id"], label=_label(m)
                            )
                            for m in self._matches
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                        custom_value=False,
                    )
                )
            }
        )
        return self.async_show_form(step_id="pick", data_schema=schema)


def _label(m: dict[str, Any]) -> str:
    parts = [m.get("adresse", "")]
    gnr, bnr = m.get("gNr"), m.get("bNr")
    fnr, snr = m.get("fNr"), m.get("sNr")
    if gnr and bnr:
        matrikkel = f"gnr {gnr}/bnr {bnr}"
        if fnr and fnr not in ("0", 0):
            matrikkel += f"/fnr {fnr}"
        if snr and snr not in ("0", 0):
            matrikkel += f"/snr {snr}"
        parts.append(f"({matrikkel})")
    return " ".join(p for p in parts if p)
