# pyOBD 3

> Modified by FareBrothers, LLC. Modifications made from 2026-04-05 onward.

pyOBD is a modern, cross-platform OBD-II diagnostic application built with Qt/QML. It is based on [pyOBD by barracuda-fsh](https://github.com/barracuda-fsh/pyobd) and the original project by Donour Sizemore.

## Features

- Live OBD-II data with searchable PID selection
- Custom dashboards with digital and dial gauges
- Multiple live graphs and session recording/replay
- Stored, pending, and permanent diagnostic trouble codes
- Freeze-frame data, readiness monitors, and Mode 06 test results
- Vehicle profiles with default dashboards
- Serial, Wi-Fi, Bluetooth SPP, custom URL, and demo connections
- Light and dark themes

## Download

Download the latest Windows, Apple Silicon macOS, or Ubuntu/Debian installer from [Releases](https://github.com/alexfare/pyobd/releases/latest). Packaged releases include the required runtime and libraries.

## Source

Python 3.8 or newer is required.

```bash
python -m pip install -r requirements.txt
python pyobd.py
```

## Connecting

Connect an ELM327-compatible adapter, turn the ignition on, open **Settings**, and select a connection method:

| Type | Target |
| --- | --- |
| Demo | Simulated vehicle; no hardware required |
| Auto detect | Searches available serial adapters |
| USB / Serial | Serial port and baud rate |
| Wi-Fi | Adapter host and port, such as `192.168.0.10:35000` |
| Bluetooth | Paired SPP/RFCOMM adapter |
| Custom URL | pyserial URL, such as `socket://192.168.0.10:35000` |

Available readings vary by vehicle. pyOBD focuses on standard engine OBD-II data and does not provide manufacturer-specific ABS, airbag, or body-module diagnostics.

## Support and security

- [Support](https://farebros.com/module.php?module=app_directory&page=support&slug=pyobd)
- [Security policy](SECURITY.md)

## License

pyOBD is licensed under GPL-2.0. See [COPYING](COPYING). Third-party components and licenses are listed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Visit [FareBrothers](https://farebros.com) for other FareBrothers projects.
