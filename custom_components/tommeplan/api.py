"""Async HTTP client for the Norconsult Tømmeplan REST API."""
from __future__ import annotations

import asyncio
import logging
from datetime import date
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)


class TommeplanApiError(Exception):
    """Base class for API errors."""


class TommeplanAuthError(TommeplanApiError):
    """Authentication failed."""


class TommeplanConnectionError(TommeplanApiError):
    """Network or transport failure."""


class TommeplanClient:
    """Thin async client around the Norconsult Tømmeplan API.

    Auth model: one POST /api/login per call session. The response carries
    `Token: <uuid>` in headers; that token is then attached to subsequent
    requests via the `Token` header.
    """

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        applikasjons_id: str,
        oppdragsgiver_id: str,
    ) -> None:
        self._session = session
        self._base = f"https://{host}/api"
        self._applikasjons_id = applikasjons_id
        self._oppdragsgiver_id = oppdragsgiver_id
        self._token: str | None = None
        self._auth_lock = asyncio.Lock()

    async def _login(self, expired_token: str | None = None) -> str:
        # Serialize logins: if a concurrent caller already refreshed the token
        # while we were waiting, reuse theirs instead of firing a second login.
        async with self._auth_lock:
            if self._token is not None and self._token != expired_token:
                return self._token
            url = f"{self._base}/login"
            payload = {
                "applikasjonsId": self._applikasjons_id,
                "oppdragsgiverId": self._oppdragsgiver_id,
            }
            try:
                async with self._session.post(
                    url, json=payload, timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    if resp.status != 200:
                        raise TommeplanAuthError(
                            f"login returned HTTP {resp.status}"
                        )
                    token = resp.headers.get("Token")
                    if not token:
                        raise TommeplanAuthError(
                            "login response missing Token header"
                        )
                    self._token = token
                    return token
            except aiohttp.ClientError as err:
                raise TommeplanConnectionError(f"login failed: {err}") from err

    async def _get(self, path: str, params: dict[str, Any]) -> Any:
        if not self._token:
            await self._login()
        url = f"{self._base}{path}"
        headers = {"Token": self._token or ""}
        try:
            async with self._session.get(
                url,
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                if resp.status == 401:
                    # Token expired — log in and retry once.
                    await self._login(expired_token=headers["Token"])
                    headers["Token"] = self._token or ""
                    async with self._session.get(
                        url,
                        params=params,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=20),
                    ) as resp2:
                        if resp2.status != 200:
                            raise TommeplanApiError(
                                f"GET {path} -> HTTP {resp2.status} after re-login"
                            )
                        return await resp2.json(content_type=None)
                if resp.status != 200:
                    raise TommeplanApiError(f"GET {path} -> HTTP {resp.status}")
                return await resp.json(content_type=None)
        except aiohttp.ClientError as err:
            raise TommeplanConnectionError(f"GET {path} failed: {err}") from err

    async def search_eiendommer(self, adresse: str) -> list[dict[str, Any]]:
        """Look up properties matching the given address fragment.

        Each result includes `id` (the eiendomId GUID we need), `adresse`, gnr/bnr.
        The API also returns `eier` (owner name) — callers should not persist it.
        """
        return await self._get("/eiendommer", {"adresse": adresse})

    async def get_tomminger(
        self, eiendom_id: str, dato_fra: date, dato_til: date
    ) -> list[dict[str, Any]]:
        """Return pickup events for a property between two dates.

        Each event is `{dato, fraksjon, fraksjonId, frekvensType, frekvensIntervall, symbolId}`.
        """
        return await self._get(
            "/tomminger",
            {
                "eiendomId": eiendom_id,
                "datoFra": dato_fra.isoformat(),
                "datoTil": dato_til.isoformat(),
            },
        )
