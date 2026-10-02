# Wanas Rekuperator — Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![HA Version](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue.svg)](https://www.home-assistant.io/)

Full control of your **Wanas recuperator** directly from Home Assistant via **Modbus** (TCP / UDP / RTU over TCP).

Monitor temperatures, airflow, fan speeds, filter status — and toggle bypass, heater, cooler, humidifier, vacation mode, fireplace, and party mode — all from your dashboard.

![Wanas-pip-boy](https://github.com/jrx-code/hassio-integration-wanas/blob/main/images/pip-boy.jpg)
---

## Features

- **55 entities** built on the manufacturer register table: airflow, five temperatures, fan
  speeds, filter countdown, the six status flags, the four digital inputs, writable
  controls for bypass, GWC, humidifier, heater, cooler, the timed functions and the fan
  power setpoints, the weekly schedule and the controller clock
- **Polish and English** entity and config-flow names, picked from the Home Assistant language
- **Asks which optional modules the unit has** (heater, cooler, humidifier, maxiCONTROL room panels) and skips their
  entities entirely when they are not fitted; changeable afterwards without re-adding
- **Three protocols**: RTU over TCP (default), plain TCP, UDP
- **Advanced mode** lets you retarget every Modbus register and rename any entity
- **Short reads**: registers are grouped into blocks of at most 16, because RS485 gateways
  stop answering long requests and one unanswered read takes down every entity
- **One exchange at a time**: reads and writes share an `asyncio.Lock`, because RTU frames
  carry no transaction id and this gateway is transparent
- **Weekly schedule, day by day, as on the panel**: five periods per day with a time of day
  where each one ends, a fan speed and a temperature; `wanas.get_schedule` /
  `wanas.set_schedule` for the whole week in one call
- **Controller clock** as a timestamp sensor, with a button that sets it from Home Assistant
- **Diagnostics** with the whole register bank, the read plan and the entity map, host redacted
- **Configurable polling interval** (5 to 600 s)
- **Auto-reconnect** on a dropped connection, and writes rejected by the device surface as a
  Home Assistant error naming the register and the value

## Installation

### HACS (recommended)

1. Open HACS → **Integrations** → three-dot menu → **Custom repositories**
2. Add this repository URL, category: **Integration**
3. Search for **Wanas** and install
4. Restart Home Assistant

### Manual

1. Copy the `custom_components/wanas` folder into your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **Wanas**
3. Enter connection details:

   | Field | Default | Description |
   |-------|---------|-------------|
   | Host | — | IP address of the recuperator |
   | Port | `502` | Modbus port |
   | Slave ID | `1` | Modbus device ID |
   | Protocol | `rtu_over_tcp` | `rtu_over_tcp`, `tcp`, or `udp` |

4. Tick only the optional modules the unit actually has. The controller answers on the
   heater, cooler and humidifier registers whether or not the modules are fitted, so their
   presence cannot be probed. Clearing one means its entities are never created:

   | Module | Entities skipped |
   |---|---|
   | Heater | `binary_sensor` heater state, `switch` heater, `number` heater days |
   | Cooler | `binary_sensor` cooler state, `switch` cooler, `number` cooler days |
   | Humidifier | `binary_sensor` humidifier state, `switch` humidifier |
   | maxiCONTROL room panels | room and bathroom 1/2 temperature and humidity `sensor`s |

   maxiCONTROL is unticked by default, and entries created before it was asked about
   treat it as absent.

5. The integration will test the connection before saving

Answers can be corrected later under **Configure** on the integration card. Turning a module
off removes its entities from the registry rather than leaving them unavailable.

### Advanced: Custom Register Addresses

If your device uses non-standard register mapping:

1. Add the integration and tick **Show advanced configuration** on the first form
2. After a successful connection test, a second step appears
3. Modify any register address (all fields are pre-filled with defaults)

The same form is available after setup: open **Configure** on the integration card and tick
**Reconfigure register addresses and names**. It opens on the values currently in use. Only
fields that differ from the defaults are stored, so an untouched field keeps following the
built-in register map when a later release corrects it, and restoring every field to its
default removes the overrides altogether.

This is useful for custom firmware or alternative Wanas device variants.

## Entities

55 entities on a fully equipped unit without maxiCONTROL: 13 sensors, 10 binary sensors,
8 switches, 18 numbers, 4 times, 1 select and 1 button. Names are translated, so the Polish column is
what a Polish instance displays.

### Sensors

| Register | English | Polish |
|---|---|---|
| 0 | Supply airflow | Wydatek nawiewu |
| 1 | Exhaust airflow | Wydatek wywiewu |
| 2 | Supply fan speed | Bieg nawiewu |
| 3 | Exhaust fan speed | Bieg wywiewu |
| 4 | Outdoor temperature | Temperatura zewnętrzna |
| 5 | Exhaust temperature | Temperatura wyrzutowa |
| 6 | Supply temperature | Temperatura nawiewu |
| 7 | Room temperature | Temperatura pomieszczenia |
| 29 | Extra probe temperature | Temperatura dodatkowa |
| 36 | Filter replacement | Wymiana filtra |
| 37 | System errors | Błędy systemu |
| 50, 51 | Controller clock | Zegar sterownika |
| 55 | Room humidity (maxiCONTROL) | Wilgotność w pokoju |
| 56 | Bathroom 1 humidity (maxiCONTROL) | Wilgotność w łazience 1 |
| 57 | Bathroom 2 humidity (maxiCONTROL) | Wilgotność w łazience 2 |
| 65 | Room temperature (maxiCONTROL) | Temperatura w pokoju |
| 66 | Bathroom 1 temperature (maxiCONTROL) | Temperatura w łazience 1 |
| 67 | Bathroom 2 temperature (maxiCONTROL) | Temperatura w łazience 2 |

Registers 55 to 57 and 65 to 67 come from a user's working Modbus setup (issue #1); the
manufacturer table in `config/hardware/` ends at register 54.

### Binary sensors

Registers 46 to 49 are the controller's read-only digital inputs.

| Register | English | Polish |
|---|---|---|
| 30 | Ground heat exchanger | Stan GWC |
| 31 | Bypass | Stan bypassu |
| 32 | Humidifier | Stan nawilżacza |
| 33 | Heater | Stan nagrzewnicy |
| 34 | Cooler | Stan chłodnicy |
| 35 | Vacation mode | Tryb urlopowy |
| 46 | Speed 1 input | Wejście biegu 1 |
| 47 | Speed 3 input | Wejście biegu 3 |
| 48 | Hood input | Wejście okapu |
| 49 | Fire alarm input | Wejście przeciwpożarowe |

### Switches

| Write → verify | English | Polish |
|---|---|---|
| 38 → 30 | Ground heat exchanger | GWC |
| 39 → 31 | Bypass | Bypass |
| 40 → 32 | Humidifier | Nawilżacz |
| 41 → 33 | Heater | Nagrzewnica |
| 42 → 34 | Cooler | Chłodnica |
| 43 → 35 | Vacation (30 days) | Urlop (30 dni) |
| 44 → 44 | Fireplace (3 min) | Kominek (3 min) |
| 45 → 45 | Party (12 h) | Impreza (12 h) |

The last three are one-tap versions of the timed functions: on writes the longest duration
the register takes, off writes 0, and the switch stays on while the counter runs down. The
numbers below set any other duration.

### Numbers

| Register | Range | Unit | English | Polish |
|---|---|---|---|---|
| 41 | 0 to 180 | dni | Heater days | Nagrzewnica (dni) |
| 42 | 0 to 180 | dni | Cooler days | Chłodnica (dni) |
| 43 | 0 to 30 | dni | Vacation days | Tryb urlopowy (dni) |
| 44 | 0 to 180 | s | Fireplace | Funkcja kominek |
| 45 | 0 to 720 | min | Party | Funkcja impreza |
| 52 | 1 to 1600 | % or m³/h | Fan power/flow 1 | Moc/przepływ biegu 1 |
| 53 | 1 to 1600 | % or m³/h | Fan power/flow 2 | Moc/przepływ biegu 2 |
| 54 | 1 to 1600 | % or m³/h | Fan power/flow 3 | Moc/przepływ biegu 3 |

Registers 52 to 54 hold fan power in percent, or the airflow in m³/h when the unit runs in
constant-flow mode. The manufacturer table gives 1 to 100 %, but a Combo 430 in flow mode
reads 100, 200 and 400 there, so the numbers accept up to 1600 and carry no unit.

Registers 41 and 42 are day counters on the device. The switches write 1, arming them
for a day; the matching Heater days / Cooler days numbers give the full 0 to 180 range
(DTR Combo 430/630, 04.2026).

The weekly schedule entities (registers 8 and 10 to 23) are described below.

## Weekly schedule and controller clock

The unit's panel calls this **Programy** (the manual: *harmonogram tygodniowy*). Each day is a
table of five periods: from, until, fan speed and temperature. Period 1 starts at 00:00 and
period 5 ends at 00:00, so there are four times to set, each the end of one period and the
start of the next.

| From | Until | Speed | Temperature |
|---|---|---|---|
| 00:00 | Period 1 until | Period 1 fan speed | Period 1 temperature |
| Period 1 until | Period 2 until | Period 2 fan speed | Period 2 temperature |
| … | … | … | … |
| Period 4 until | 00:00 | Period 5 fan speed | Period 5 temperature |

The controller keeps a separate schedule for each day but shows one day at a time: register 8
selects the day, and registers 10 to 23 read and write that day. Register 8 is **not** the
current weekday. This was checked on a Combo 430: with Saturday selected, period 1 speed was
changed from 2 to 1, Sunday and Friday still read 2, and Saturday kept 1 after stepping
through the other days. The value was then put back.

| Entity | Register | English | Polish |
|---|---|---|---|
| `select` | 8 | Schedule day | Harmonogram: dzień |
| `time` | 10-13 | Period 1-4 until | Przedział 1-4: do godziny |
| `number` | 14-18 | Period 1-5 fan speed | Przedział 1-5: bieg |
| `number` | 19-23 | Period 1-5 temperature | Przedział 1-5: temperatura |
| `sensor` | 8, 10-23 | Schedule (selected day) | Harmonogram (wybrany dzień) |
| `button` | 50, 51 | Set clock from Home Assistant | Ustaw zegar z Home Assistant |

- All period entities act on the day the **Schedule day** select shows. Pick the day first,
  then change the periods. Changing the select does not change what the unit runs today.
- **Until** times must be on the quarter hour, between 00:15 and 23:45, and later than the
  previous period's end and earlier than the next one's. Anything else is rejected with an
  error that says why. Nothing is rounded.
- Each **fan speed** entity carries `from` and `until` attributes.
- The **Schedule** sensor reads like the panel's table, for example
  `00:00-06:00 I 18° | 06:00-07:00 II 20° | 07:00-14:00 I 20° | 14:00-15:00 III 20° | 15:00-00:00 I 18°`,
  with the day and the five periods as attributes.

For whole-week work there are two services. Both hold the bus for the whole exchange and put
register 8 back where it was:

```yaml
# Read all seven days: {monday: {periods: [{from, until, speed, temperature}, ...]}, ...}
action: wanas.get_schedule
response_variable: week

# Write whole days, one row per period, like the panel's table
action: wanas.set_schedule
data:
  days: [monday, tuesday, wednesday, thursday, friday]
  periods:
    - {until: "06:00", speed: 1, temperature: 18}
    - {until: "07:00", speed: 2, temperature: 20}
    - {until: "14:00", speed: 1, temperature: 20}
    - {until: "15:00", speed: 3, temperature: 20}
    - {speed: 1, temperature: 18}        # period 5 runs to midnight
```

All five periods are required. Speeds are 0-3, temperatures 10-30 °C, and `until` follows
the rules above. Pass `config_entry_id` only when more than one unit is set up.

The controller clock is local wall time: date `day<<11 | month<<7 | (year-2000)` in register
50, time `hour<<8 | minute` in register 51. The time example in the DTR (`hour<<7`) does not
match the unit. The clock drifts by a few minutes, and the weekly schedule runs on it.

The DTR also lists registers 72 (manual fan speed), 73 (manual temperature setpoint) and 74
(software version). The Combo 430 this was developed on answers all three with a Modbus
error, so they are not exposed.

## Requirements

- **Home Assistant 2024.7 or newer.** The advanced step uses `data_entry_flow.section`,
  which is defined in `homeassistant/data_entry_flow.py` from 2024.7.0 and is absent in
  2024.6.0. The coordinator also lives in `ConfigEntry.runtime_data`, which landed earlier.
- **pymodbus 3.10 or newer** (installed automatically). Release 3.10.0 renamed the client
  parameter `slave=` to `device_id=`, which is what this code calls.
- Network access to the recuperator over Modbus TCP or UDP.

## No fan or climate entity, and why

There is no register that sets the fan speed. Registers 2 and 3 report it, registers 46 and 47
are read-only digital inputs, and the speed itself comes either from those contacts or from
the weekly schedule. A `fan` entity could only fake it by rewriting the active period's speed,
which would silently edit the schedule instead of making a temporary change. The weekly
schedule is exposed as configuration entities instead, and on this installation the contacts
are driven by a Zigbee relay outside the integration.

The same applies to `climate`: the unit has no target-temperature register for the supply
air, only per-period setpoints in the weekly schedule.

## Tests

```bash
python3 -m venv .venv && .venv/bin/pip install pytest-homeassistant-custom-component pymodbus
.venv/bin/python -m pytest
```

26 tests covering the config and options flows (including remapping registers after setup),
setup, the version 2 migration, module gating, read blocking, bus serialisation, error
mapping and diagnostics. Coverage is 93 % overall and 95 % on `config_flow.py`.

## Languages

Entity names and the config flow are translated into **English** and **Polish**; Home
Assistant picks the language from the instance setting. Renaming an entity in the advanced
register step overrides the translation for that entity only.

Adding a language means one file in `custom_components/wanas/translations/` with the same
keys as `strings.json`. The `entity` block carries all 34 entity names.

## Troubleshooting

**"Cannot connect to the device"**
- Verify the IP address is reachable (`ping <host>`)
- Check Modbus port (default 502) is not blocked by firewall
- Confirm Slave ID matches device configuration
- Try switching protocol (some devices prefer plain TCP over RTU)

**Sensors show "Unknown"**
- The device may not support all registers — this is normal for some variants
- In Advanced Mode, you can remap registers to match your device

## License

MIT License — see [LICENSE](LICENSE) for details.

## Author

**JI ENGINEERING**

---

<sub>Built with Modbus and determination. Działa jak złoto.</sub>
