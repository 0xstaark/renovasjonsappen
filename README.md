# Tømmeplan – Home Assistant integration for Time kommune

A Home Assistant custom integration that fetches your household waste collection schedule from Norconsult Digital's *Renovasjon Time kommune* app backend.

For an address in Time kommune you get:

- one **sensor per fraksjon** (Restavfall, Matavfall, Papir, Glassemballasje, …), state = the next pickup date, attributes include `days_until` and `all_upcoming`
- one **calendar entity** containing every upcoming pickup as an all-day event
- automatic daily refresh of the schedule for the next 12 months in a single API call

The integration only contacts `renovasjon.time.kommune.no`; nothing is sent anywhere else.

## Installation

### HACS (custom repository)

1. HACS → ⋮ → *Custom repositories* → add `https://github.com/0xstaark/renovasjonsappen` as type *Integration*
2. Install **Tømmeplan**, then restart Home Assistant
3. *Settings → Devices & Services → Add Integration → "Tømmeplan"*

### Manual

1. Copy `custom_components/tommeplan/` into your Home Assistant config directory so the final path is `<ha_config>/custom_components/tommeplan/`
2. Restart Home Assistant
3. *Settings → Devices & Services → Add Integration → "Tømmeplan"*

## Setup walkthrough

The config flow has two steps:

1. Type your **address** (e.g. `Eksempelveien 1`). The integration calls the Tømmeplan backend and validates the address against the official Norwegian property register (matrikkelen). Results are limited to Time kommune.
2. **Pick your property** from the dropdown of real matches. The integration stores only the resulting `eiendomId` (a GUID); your address is just used as a label.

After setup the integration creates one device per property with sensors and a calendar entity. The schedule refreshes once every 24 hours.

## Automation example

Notify the day before any pickup:

```yaml
automation:
  - alias: Påminnelse om tømming i morgen
    trigger:
      - platform: time
        at: "18:00:00"
    condition:
      - condition: template
        value_template: >
          {{ state_attr('sensor.tommeplan_restavfall', 'days_until') == 1
             or state_attr('sensor.tommeplan_matavfall', 'days_until') == 1
             or state_attr('sensor.tommeplan_papir', 'days_until') == 1
             or state_attr('sensor.tommeplan_glassemballasje', 'days_until') == 1 }}
    action:
      - service: notify.mobile_app
        data:
          title: Tømming i morgen
          message: >
            {% set fracs = [
              ('Restavfall', state_attr('sensor.tommeplan_restavfall', 'days_until')),
              ('Matavfall', state_attr('sensor.tommeplan_matavfall', 'days_until')),
              ('Papir', state_attr('sensor.tommeplan_papir', 'days_until')),
              ('Glassemballasje', state_attr('sensor.tommeplan_glassemballasje', 'days_until'))
            ] %}
            {{ fracs | selectattr(1, 'eq', 1) | map(attribute=0) | join(', ') }}
```

## How it works

```
Setup (one time):
  client.search_eiendommer("Eksempelveien 1")   →  pick eiendomId

Daily refresh:
  POST /api/login                               →  Token header
  GET  /api/tomminger?eiendomId=…&datoFra=…&datoTil=…
```

The integration logs in once and reuses the token across refreshes. If the token expires (HTTP 401), it transparently re-authenticates and retries the call once. The token comes back as a *response header* (`Token:`), not in the body.

## Legal and ethical notes

This integration was developed for personal use, to pull *your own* household's pickup schedule into your own smart-home setup. The integration only ever stores and exposes data about the property you configure.

The backend used by the Renovasjon Time kommune app is not officially published. If Time kommune or Norconsult Digital would like the integration changed or removed, please open an issue.

## License

MIT
