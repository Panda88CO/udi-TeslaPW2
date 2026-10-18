# Tesla PowerWall Node Server for Polyglot PG3x

**Version:** 0.3.0  
**Author:** Panda88CO  

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

- **Controller Node (`CONTROLLER` - Tesla PowerWall Info)**:
  - `ST`: Controller Up
  - `GV2`: Connected to Tesla Power Wall
  - `GV3`: Consecutive missed LongPolls
  - `GV4`: Connection Status (No Connection, Cloud only, Local only, Local and Cloud)

- **Status Node (`PWSTATUS` - Power Wall Status)**:
  - `ST`: Connected to Tesla (Online status)
  - `GV0`: Remaining Battery (%)
  - `GV1`–`GV4`: Inst Solar Export, Inst Battery Export, Inst Home Load, Inst Grid Import (kW)
  - `GV5`: Operation Mode (Backup, Self-consumption, Autonomous, Site control)
  - `GV6`: Grid Status (On grid, Islanded ready, Islanded, Transition to grid)
  - `GV7`: Grid Services Active
  - `GV8`–`GV14`: Today's energy totals (kWh)
  - `GV28`: Generator Today (kWh) *(conditionally displayed only if generator is installed)*
  - `TIME`: Last Update Time (Unix timestamp)

- **Usage History Node (`PWHISTORY` - Power Wall History)**:
  - **`ST`**: Home Total Use Today (kWh) — primary status displayed in IoX tree and summary views
  - **`GV0`**: Connected to Tesla (Online status)
  - **`GV8`**: Home Total Use Today (kWh) — symmetrical pair to GV15
  - **`GV9`–`GV21`**: Today and Yesterday energy totals (kWh)
  - **`GV22`–`GV25`**: Backup event counts and duration
  - **`GV26`–`GV29`**: EV charging power and time
  - **`GV2`**: Generator Yesterday (kWh) *(conditionally displayed only if generator is installed)*

- **Control Parameters Node (`PWSETUP` - Power Wall Control Parameters)**:
  - **`ST`**: Operating Mode (Backup, Self-consumption, Autonomous) — primary status & control
  - **`GV1`**: Backup Reserve (%)
  - **`GV3`**: Storm Mode
  - **`GV5`**: Grid Import to battery
  - **`GV6`**: Grid Export Mode
  - **`GV7`**: EV offgrid charge reserve (%)

*Note: Generator drivers are dynamically hidden in IoX if no generator is installed.*

---

## Support & Contributions
If additional functionality is desired, contact the author through GitHub: [https://github.com/Panda88CO/udi-TeslaPW2](https://github.com/Panda88CO/udi-TeslaPW2)
