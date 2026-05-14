from __future__ import annotations

from datetime import timedelta

DOMAIN = "tommeplan"

CONF_KOMMUNE = "kommune"
CONF_EIENDOM_ID = "eiendom_id"
CONF_ADRESSE = "adresse"

DEFAULT_SCAN_INTERVAL = timedelta(hours=24)
SCHEDULE_LOOKAHEAD_DAYS = 365

# Time kommune backend config.
KOMMUNER: dict[str, dict[str, str]] = {
    "time": {
        "name": "Time kommune",
        "kommunenr": "1121",
        "host": "renovasjon.time.kommune.no:8055",
        "applikasjonsId": "2de50fc8-4ab7-426b-99cd-a5ddd0de71d1",
        "oppdragsgiverId": "100",
    },
}

# Icon per fraksjon. Falls back to mdi:trash-can.
ICON_MAP: dict[str, str] = {
    "Restavfall": "mdi:trash-can",
    "Matavfall": "mdi:food-apple",
    "Bioavfall": "mdi:leaf",
    "Papir": "mdi:newspaper-variant-multiple",
    "Papp": "mdi:archive",
    "Pappogkartong": "mdi:archive",
    "Drikkekartong": "mdi:cup",
    "Plast": "mdi:recycle",
    "Plastemballasje": "mdi:recycle",
    "Glassemballasje": "mdi:bottle-soda",
    "Glassogmetall": "mdi:bottle-soda",
    "Metall": "mdi:silverware-fork-knife",
    "Hageavfall": "mdi:leaf",
    "Parkoghageavfall": "mdi:leaf",
    "Farligavfall": "mdi:biohazard",
    "Elektroniskavfall": "mdi:chip",
    "Trevirke": "mdi:tree",
    "Juletre": "mdi:pine-tree",
}
