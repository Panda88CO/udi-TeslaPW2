# Tesla PowerWall Node Server for Polyglot PG3x

## Installation
Cloud access via the official Tesla Fleet API is enabled by default with zero configuration required. The node server automatically discovers your account region directly through the Tesla Fleet API.

Simply install the node server in PG3x and click the **Authenticate** button. You will be redirected to Tesla's secure login page to grant access. The following scopes are requested:

- `energy_device_data`
- `energy_cmds`
- `openid`
- `offline_access`

### Optional: Local LAN Access (Powerwall 2 only)
For Powerwall 2 installations with gateways that support customer local API access (`/api/login/Basic`), local LAN communication can optionally be enabled by adding the following parameters in PG3x Custom Configuration:

- `LOCAL_IP_ADDRESS`: IP address of the Powerwall Gateway (e.g. `192.168.1.150`)
- `LOCAL_USER_EMAIL`: Customer email used for gateway login
- `LOCAL_USER_PASSWORD`: Customer password used for gateway login

If these parameters are present, the node server tests local connectivity on startup and uses local LAN telemetry if available. If local access is unsupported or fails (such as on Powerwall 3), it gracefully falls back to Cloud access without interruption.

---

## Node Structure & Key Drivers

- **Controller Node (`CONTROLLER`)**: System status, connection state (`GV4`), and poll health.
- **Status Node (`PWSTATUS`)**: Live power flows in kW (`GV1`–`GV4`), battery SOC (`GV0`), operating mode (`GV5`), grid state (`GV6`), and today's energy totals (`GV8`–`GV14`).
- **Usage History Node (`PWHISTORY`)**:
  - **`ST`**: Home Total Use Today (kWh) — primary status displayed in IoX tree views
  - **`GV0`**: Connected to Tesla / Online status
  - **`GV8`**: Home Total Use Today (kWh)
  - **`GV9`–`GV21`**: Today and Yesterday energy totals (kWh)
  - **`GV22`–`GV29`**: Backup event counts/durations and EV charging power/time
- **Control Parameters Node (`PWSETUP`)**:
  - **`ST`**: Operating Mode (Backup, Self-consumption, Autonomous)
  - **`GV1`**: Backup Reserve (%)
  - **`GV3`**: Storm Mode
  - **`GV5`**: Grid Import to Battery
  - **`GV6`**: Grid Export Mode
  - **`GV7`**: EV Off-Grid Charge Reserve (%)

*Note: Generator drivers are dynamically hidden in IoX if no generator is installed.*

---

## Support & Contributions
If additional functionality is desired, contact the author through GitHub: [https://github.com/Panda88CO/udi-TeslaPW2](https://github.com/Panda88CO/udi-TeslaPW2)
