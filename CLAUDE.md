# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Home Assistant integration for a **Wanas heat recovery ventilator (HRV)** controlled via **Modbus RTU over TCP**. This is a YAML-only configuration project (no build system, no tests, no linting) — all files are Home Assistant configuration that get imported via `packages:` or merged into `configuration.yaml`.

## Architecture

```
config/
├── sensors/0_wanas.yaml          # Core Modbus config: 27 sensors + 7 switches
├── automations/
│   ├── ventilation.yaml          # CO₂, humidity, hood, window-based fan control
│   ├── ac.yaml                   # Cooling with hysteresis + presence detection
│   └── heating.yaml              # Time-based heating schedule (night/day presets)
├── hardware/
│   ├── modbus-registers.json     # Complete Modbus register map (54 registers, 0–54)
│   ├── default-sensors-modbus-registers.yaml
│   └── waveshare-485-eth.json    # RS232/485 converter backup config
└── helpers/                      # Reserved, currently empty
examples/                         # Reference automations, dashboard, RTU serial config
```

**Modbus layer** (`config/sensors/0_wanas.yaml`) is the foundation — it defines the TCP connection (host from `!secret wanas_modbus_url`, port 502, slave 1) and all sensor/switch entities. The three automation files consume these entities plus external sensors (CO₂, humidity, power, window contacts, presence).

### Modbus Register Layout

- **0–7**: Real-time data (airflow m³/h, fan speeds 0–3, temperatures with 0.1°C scale via int16)
- **8–28**: Weekly schedule (day, zone boundaries in minutes, zone speeds, zone temps, comm params)
- **29–36**: Read-only status (extra temp, GWC, bypass/humidifier/heater/cooler/vacation states, filter days remaining, error bits)
- **37–45**: Writable controls — switches mapped to HA entities (bypass=39, humidifier=40, heater=41, cooler=42, vacation=43, fireplace=44, party=45)
- **46–54**: Digital input feedback, date/time, power/flow percentages per speed

Temperature registers use uint16 where 0=0°C, 65535=−0.1°C, and 63066=sensor error.

## Conventions

- **Entity naming**: Polish user-facing labels ("Wydatek nawiewu"), English snake_case unique IDs with `wanas_` prefix (`wanas_wydatek_nawiewu`)
- **Automation structure**: Descriptive `alias` + `description`, triggers with `id` labels, `choose`/`when` for conditional routing, local `variables` for thresholds, `mode: single`
- **Modbus switches**: Use `verify` loops to confirm command execution
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
- `switch.sterownik_rekuperacji_l2` (speed 3 / "L2 - Bieg 3"), `switch.sterownik_rekuperacji_l3` (hood/fireplace mode / "L3 - Tryb okap/kominek") — Z2M MQTT switches on HRV digital inputs (TS0004 4-gang relay, IEEE `0xa4c138b7a45d8cd7`)
- `climate.*` entities labeled `hvac`, `scene.stan_termostatow`

## Modbus Connection Settings

- Protocol: Modbus RTU over TCP (alternative: pure RTU serial at `/dev/ttyUSB0`, 38400 baud 8E1 — see `examples/modbus_rtu.yaml`)
- Default: port 502, slave 1, timeout 5000ms, message_wait 200ms, delay 2s
- Hardware: Waveshare RS232/485 WiFi/ETH converter (config in `config/hardware/waveshare-485-eth.json`)
