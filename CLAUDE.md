# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Home Assistant integration for a **Wanas heat recovery ventilator (HRV)** controlled via
**Modbus RTU over TCP**. The repository holds two things: the `custom_components/wanas`
Python integration, which is what ships via HACS, and a `config/` tree of the older YAML
setup kept for reference. No build system, no tests, no linting.

## Architecture

```
custom_components/wanas/
├── const.py                      # register map: 17 sensors, 10 binary sensors,
│                                 #   5 switches, 8 numbers, all keyed to registers
├── coordinator.py                # pymodbus client, read blocks capped at 16 registers
├── config_flow.py                # connection step + optional register/name overrides
├── {sensor,binary_sensor,switch,number}.py
├── strings.json                  # English source for config flow and entity names
└── translations/{en,pl}.json     # entity names are TRANSLATED, see the warning below

config/                           # legacy YAML setup, not shipped
├── sensors/0_wanas.yaml          # Core Modbus config: 27 sensors + 7 switches
├── automations/
│   ├── ventilation.yaml          # CO₂, humidity, hood, window-based fan control
│   ├── ac.yaml                   # Cooling with hysteresis + presence detection
│   └── heating.yaml              # Time-based heating schedule (night/day presets)
├── hardware/
│   ├── modbus-registers.json     # Complete Modbus register map (54 registers, 0–54)
│   └── default-sensors-modbus-registers.yaml
examples/                         # Reference automations, dashboard, RTU serial config
```

### The register table is the authority

`config/hardware/modbus-registers.json` is a transcription of the manufacturer table and is
the source of truth. **`docs/4. Przełączniki.txt` contradicts it on registers 41 to 48 and is
wrong**: 41 and 42 are day counters, not booleans; 43 caps at 30 days, not 255; 44 is in
seconds, not minutes; 46 to 49 are read-only digital inputs, not setpoints; the real fan
power setpoints are 52 to 54. `const.py` followed the text file until 2026-09-04 and wrote to
read-only registers, which the device answered with Modbus exception 0x02.

### Entity names come from translations, not from code

Every entity sets `_attr_translation_key` and must **not** set `_attr_name` unless the user
renamed it in the advanced register step. `Entity._name_internal` returns `_attr_name` first
if the attribute exists at all, so assigning it unconditionally silently kills every
translation. Names live in `strings.json` and `translations/*.json` under `entity.<platform>.<key>.name`.

### Entity identity

Entity and device unique ids are `f"{entry.unique_id}_{key}"`, where `entry.unique_id` is
`host:port:slave_id`. Never go back to `entry_id`: it changes when the integration is removed
and re-added, orphaning every entity with its history. `async_migrate_entry` moves version 1
entries across; anything that builds those ids (the module purge in `__init__.py`, for one)
must use `device_key(entry)` from `entity.py`.

### Testing

Develop against a Modbus mock server and a test Home Assistant instance, never against the
real unit: a Waveshare gateway in transparent mode broadcasts RS485 responses to every
connected TCP socket, so a second Modbus master corrupts Home Assistant's readings.

`pytest` runs against `pytest-homeassistant-custom-component` in a venv; the suite mocks the
pymodbus client, so it needs no hardware and no mock server.

### Modbus Register Layout

- **0–7**: Real-time data (airflow m³/h, fan speeds 0–3, temperatures with 0.1°C scale via int16)
- **8–28**: Weekly schedule (day, zone boundaries in minutes, zone speeds, zone temps, comm params)
- **29–36**: Read-only status (extra temp, GWC, bypass/humidifier/heater/cooler/vacation states, filter days remaining, error bits)
- **38–45**: Writable controls (GWC=38, bypass=39, humidifier=40, heater=41 in days,
  cooler=42 in days, vacation=43 in days, fireplace=44 in seconds, party=45 in minutes)
- **46–49**: Read-only digital inputs (speed 1, speed 3, hood, fire alarm)
- **50–51**: Date and time. The manufacturer's encoding tables are NOT in `docs/`; the mock
  assumes `(month << 8) | day` and `(hour << 8) | minute`, unverified against hardware
- **52–54**: Fan power / flow setpoints per speed, 1 to 100 %

Temperature registers use uint16 where 0=0°C, 65535=−0.1°C, and 63066=sensor error.

## Conventions

- **Entity naming**: Polish user-facing labels ("Wydatek nawiewu"), English snake_case unique IDs with `wanas_` prefix (`wanas_wydatek_nawiewu`)
- **Automation structure**: Descriptive `alias` + `description`, triggers with `id` labels, `choose`/`when` for conditional routing, local `variables` for thresholds, `mode: single`
- **Switch verify addresses**: a switch writes to its control register and reads its state
  back from the matching status register (38→30, 39→31, 40→32, 41→33, 42→34)
- **Secrets**: Modbus host IP stored in `secrets.yaml` as `wanas_modbus_url`

## Key Thresholds (defined as variables in automation files)

| Parameter | High | Low | File |
|-----------|------|-----|------|
| CO₂ | 1000 ppm (5 min) → speed 3 | 800 ppm (2 min) → speed 1 | ventilation.yaml |
| Humidity | 65% (5 min) → speed 3 | 55% (5 min) → normalize | ventilation.yaml |
| Hood power | >25W (5s) → hood mode | <10W (5s) → off | ventilation.yaml |
| Cooling ON | >25°C (10 min) + presence | — | ac.yaml |
| Cooling OFF | <22°C (10 min) | coil <18°C / outdoor <15°C | ac.yaml |

## Required External Entities

The automations depend on entities not defined in this repo (they come from other HA integrations):
- `sensor.poziom_co2`, `sensor.poziom_wilgotnosci_dom`, `sensor.gniazdo_okap_power`
- `binary_sensor.domownicy_sa_w_domu` (presence)
- 8 window contact sensors (`binary_sensor.czujniki_okna_*`)
- `switch.sterownik_rekuperacji_l2` (speed 3 / "L2 - Bieg 3"), `switch.sterownik_rekuperacji_l3` (hood/fireplace mode / "L3 - Tryb okap/kominek") — Z2M MQTT switches on HRV digital inputs (TS0004 4-gang relay; use your own device's IEEE address)
- `climate.*` entities labeled `hvac`, `scene.stan_termostatow`

## Modbus Connection Settings

- Protocol: Modbus RTU over TCP (alternative: pure RTU serial at `/dev/ttyUSB0`, 38400 baud 8E1 — see `examples/modbus_rtu.yaml`)
- Default: port 502, slave 1, timeout 5000ms, message_wait 200ms, delay 2s
- Hardware: Waveshare RS232/485 WiFi/ETH converter
