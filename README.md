# Wanas Rekuperator — Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![HA Version](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue.svg)](https://www.home-assistant.io/)

Full control of your **Wanas recuperator** directly from Home Assistant via **Modbus** (TCP / UDP / RTU over TCP).

Monitor temperatures, airflow, fan speeds, filter status — and toggle bypass, heater, cooler, humidifier, vacation mode, fireplace, and party mode — all from your dashboard.

![Wanas-pip-boy](https://github.com/jrx-code/hassio-integration-wanas/blob/main/images/pip-boy.jpg)
---

## Features

- **19 sensors** — supply/exhaust airflow, 5 temperature readings, fan speeds, bypass/heater/cooler/humidifier states, filter countdown, party timer, hood state
- **7 switches** — bypass, humidifier, heater, cooler, vacation, fireplace, party
- **3 protocols** — RTU over TCP (default), plain TCP, UDP
- **Advanced mode** — full Modbus register address customization for non-standard device configurations
- **Efficient polling** — automatic grouping of register reads into contiguous blocks to minimize Modbus traffic
- **Auto-reconnect** — handles connection drops gracefully

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

4. The integration will test the connection before saving

### Advanced: Custom Register Addresses

If your device uses non-standard register mapping:

1. Enable **Advanced Mode** in your Home Assistant user profile
2. Add the integration — after successful connection test, a second step appears
3. Modify any register address (all fields are pre-filled with defaults)

This is useful for custom firmware or alternative Wanas device variants.

## Entities

### Sensors

| Entity | Register | Unit | Description |
|--------|----------|------|-------------|
| Wydatek nawiewu | 0 | m³/h | Supply airflow |
| Wydatek wywiewu | 1 | m³/h | Exhaust airflow |
| Bieg nawiewu | 2 | — | Supply fan speed |
| Bieg wywiewu | 3 | — | Exhaust fan speed |
| Temperatura zewnętrzna | 4 | °C | Outdoor temperature |
| Temperatura wyrzutowa | 5 | °C | Exhaust temperature |
| Temperatura nawiewu | 6 | °C | Supply temperature |
| Temperatura wewnątrz | 7 | °C | Indoor temperature |
| Aktualna temperatura | 29 | °C | Current temperature |
| Stan bypass | 31 | — | Bypass state |
| Stan nawilżacza | 32 | — | Humidifier state |
| Stan nagrzewnicy | 33 | — | Heater state |
| Stan chłodnicy | 34 | — | Cooler state |
| Tryb urlopowy | 35 | — | Vacation mode |
| Wymiana filtra | 36 | days | Filter replacement countdown |
| Impreza (czas) | 45 | min | Party time remaining |
| Bieg I | 46 | — | Fan speed level 1 |
| Bieg III | 47 | — | Fan speed level 3 |
| Okap — stan | 48 | — | Hood state |

### Switches

| Entity | Write → Verify | ON / OFF values |
|--------|---------------|-----------------|
| Bypass | 39 → 31 | 1 / 0 |
| Nawilżacz | 40 → 32 | 1 / 0 |
| Nagrzewnica | 41 → 33 | 1 / 0 |
| Chłodnica | 42 → 34 | 1 / 0 |
| Urlop | 43 → 35 | 30 / 0 |
| Kominek | 44 → 44 | 180 / 0 |
| Impreza | 45 → 45 | 720 / 0 |

## Requirements

- Home Assistant 2024.1+
- Network access to Wanas recuperator (Modbus TCP/UDP)
- Python dependency: `pymodbus >= 3.5.0` (installed automatically)

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
