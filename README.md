# SolarManager MyStrom Bridge

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

A Home Assistant custom integration that bridges a [virtual MyStrom Energy Control Switch](https://github.com/neuhausf/solar-manager-virtual-device) to Home Assistant entities via UI config flow.

## Features

- **Switch entity** – reflects the relay state of the virtual device; toggling the switch calls `/relay?state=1|0` on the device.
- **Power sensor entity** – exposes the current power reading (W) returned by `/report`.
- **Automatic polling** – polls `/report` at a configurable interval (default: 5 s) and keeps the HA entities in sync.
- **Power forwarding** – optionally tracks any HA sensor entity (e.g. a real smart-plug power sensor) and forwards its value to the virtual device's `POST /power` endpoint every time it changes.
- **Options flow** – polling interval and power source entity can be changed at any time without removing the integration.

## Installation via HACS

1. In HACS → *Integrations* → ⋮ → *Custom repositories*, add  
   `https://github.com/neuhausf/solarmanager-mystrom-bridge` as **Integration**.
2. Install *SolarManager MyStrom Bridge* from HACS.
3. Restart Home Assistant.

## Setup

1. Go to *Settings → Devices & Services → Add Integration*.
2. Search for **SolarManager MyStrom Bridge**.
3. Enter:
   - **Name** – friendly name shown in HA.
   - **IP Address / Hostname** – the address of the virtual MyStrom device (must be reachable from HA).
   - **Polling Interval** – how often to query `/report` (default 5 s).
4. Optionally select a **Power Sensor Entity** whose value (in W) will be forwarded to the device via `POST /power`.

## Virtual Device API (summary)

| Method | Resource | Description |
|--------|----------|-------------|
| `GET` | `/report` | Returns `{"power": <W>, "relay": <bool>}` |
| `GET` | `/relay?state=1` | Turn relay on |
| `GET` | `/relay?state=0` | Turn relay off |
| `GET` | `/toggle` | Toggle relay |
| `POST` | `/power` | Body: `{"power": <W>}` – set current power |

See [solar-manager-virtual-device](https://github.com/neuhausf/solar-manager-virtual-device) for setup instructions.

## License

MIT
