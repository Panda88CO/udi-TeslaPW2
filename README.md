# udi-TeslaPW2 - Polyglot PG3x Node Server for Tesla Powerwall

**Version:** 0.3.1  
**Platform:** Universal Devices eisy / Polisy with Polyglot PG3x (v3.x)  
**Author:** Panda88CO  

This is an updated version of the Tesla Powerwall Node Server for Universal Devices eisy / Polisy running **Polyglot PG3x** (v3.x). It integrates with the official **Tesla Fleet API** for cloud monitoring and control, with optional local LAN gateway telemetry for Powerwall 2 systems.

## Key Features

- **Official Tesla Fleet API Integration**: Direct OAuth authentication and cloud telemetry/control via Tesla's Fleet API.
- **Zero-Config Cloud Discovery**: Automatically discovers your account region (NA, EU, or CN) on initial authentication.
- **Optional Local LAN Telemetry (Powerwall 2)**: Direct high-speed local polling from the Powerwall Gateway API when configured, with automatic fallback to cloud telemetry.
- **Dynamic Node Profiles**: Sub-nodes and driver sets automatically adapt based on your system configuration (e.g., hiding generator drivers if no generator is installed).
- **Explicit Driver Names**: All node drivers define explicit descriptive names matching dynamic profiles and NLS definitions for seamless PG3x and IoX presentation.
- **Comprehensive Telemetry**: Real-time power flows (kW), daily/historical energy usage (kWh), backup events, and EV charging telemetry.

---

## Installation & Configuration

### Prerequisites
- Polyglot PG3x (this node server requires PG3x and will not run on legacy PG3).
- Tesla account with one or more registered Powerwall energy sites.

### 1. Cloud Installation (Recommended / Default)
Cloud access requires zero initial configuration:
1. Install **Tesla PowerWall** from the PG3x Node Server Store.
2. In the PG3x dashboard, click the **Authenticate** button.
3. You will be redirected to Tesla's secure login page. Log in and approve access for the following scopes:
   - `energy_device_data`
   - `energy_cmds`
   - `openid`
   - `offline_access`
4. The node server will automatically discover your region and initialize all registered Powerwall sites.

### 2. Optional: Local LAN Access (Powerwall 2 only)
If you have a Powerwall 2 with a gateway that supports customer local API access (`/api/login/Basic`), you may optionally configure:
- In PG3x Custom Configuration, specify:
  - `LOCAL_IP_ADDRESS`: Gateway local IP address (e.g. `192.168.1.150`)
  - `LOCAL_USER_EMAIL`: Customer email used for gateway login
  - `LOCAL_USER_PASSWORD`: Customer password used for gateway login

The node server verifies local connectivity on startup. If local access is available, it uses high-frequency local meter telemetry; if local access is unavailable or unsupported (such as on Powerwall 3), it seamlessly falls back to Cloud access without interruption.

---

## Node Structure & Drivers

The node server creates a primary controller node, plus a set of sub-nodes for each detected Powerwall energy site:

### 1. Controller Node (`CONTROLLER` - Tesla PowerWall Info)
Main node server status and connectivity monitor.
- **`ST`**: Controller Up (`Up` / `Down`)
- **`GV2`**: Connected to Tesla Power Wall (`Not Connected` / `Connected`)
- **`GV3`**: Consecutive Missed LongPolls (Count)
- **`GV4`**: Connection Status (`No Connection`, `Cloud only`, `Local only`, `Local and Cloud`)
- **Commands**:
  - `UPDATE`: Forces an immediate query and update of system data.

### 2. Status Node (`PWSTATUS` - Power Wall Status)
Live status, instantaneous power flows, and current operation modes.
- **`ST`**: Connected to Tesla / Online (`offline` / `online`)
- **`GV0`**: Remaining Battery (`%`)
- **`GV1`**: Inst Solar Export (`kW`)
- **`GV2`**: Inst Battery Export (`kW`)
- **`GV3`**: Inst Home Load (`kW`)
- **`GV4`**: Inst Grid Import (`kW`)
- **`GV5`**: Operation Mode (`backup`, `self consumption`, `autonomous`, `site control`)
- **`GV6`**: Grid Status (`on grid`, `islanded ready`, `islanded`, `transition to grid`)
- **`GV7`**: Grid Services Active (`Disabled` / `Enabled`)
- **`GV8`**: Home Total Use Today (`kWh`)
- **`GV9`**: Solar Export Today (`kWh`)
- **`GV10`**: Battery Export Today (`kWh`)
- **`GV11`**: Battery Import Today (`kWh`)
- **`GV12`**: Grid Export Today (`kWh`)
- **`GV13`**: Grid Import Today (`kWh`)
- **`GV14`**: Grid/House Net Use Today (`kWh`)
- **`GV28`**: Generator Today (`kWh`) *(conditionally displayed only if a generator is installed)*
- **`TIME`**: Last Update Time (Unix timestamp)
- **Commands**: `UPDATE`

### 3. Usage History Node (`PWHISTORY` - Power Wall History)
Daily and historical energy consumption, backup events, and EV charging data.
- **`ST`**: Home Total Use Today (`kWh`) — *Primary status shown in IoX tree and summary views*
- **`GV0`**: Connected to Tesla (`offline` / `online`)
- **`GV8`**: Home Total Use Today (`kWh`) — *Preserved for symmetry with GV15*
- **`GV9`**: Solar Export Today (`kWh`)
- **`GV10`**: Battery Export Today (`kWh`)
- **`GV11`**: Battery Import Today (`kWh`)
- **`GV12`**: Grid Export Today (`kWh`)
- **`GV13`**: Grid Import Today (`kWh`)
- **`GV14`**: Grid/House Net Use Today (`kWh`)
- **`GV15`**: Home Total Use Yesterday (`kWh`)
- **`GV16`**: Solar Export Yesterday (`kWh`)
- **`GV17`**: Battery Export Yesterday (`kWh`)
- **`GV18`**: Battery Import Yesterday (`kWh`)
- **`GV19`**: Grid Export Yesterday (`kWh`)
- **`GV20`**: Grid Import Yesterday (`kWh`)
- **`GV21`**: Grid/House Net Use Yesterday (`kWh`)
- **`GV22`**: Today nbr backup events (Count)
- **`GV23`**: Today backup event time (Duration in seconds)
- **`GV24`**: Yesterday nbr backup events (Count)
- **`GV25`**: Yesterday backup event time (Duration in seconds)
- **`GV26`**: Today charge power (`kWh`)
- **`GV27`**: Today charge time (Duration in seconds)
- **`GV28`**: Yesterday charge power (`kWh`)
- **`GV29`**: Yesterday charge time (Duration in seconds)
- **`GV2`**: Generator Yesterday (`kWh`) *(conditionally displayed only if a generator is installed)*
- **Commands**: `UPDATE`

### 4. Control Parameters Node (`PWSETUP` - Power Wall Control Parameters)
Allows controlling Powerwall operating parameters from IoX / ISY programs and admin console.
- **`ST`**: Operating Mode (`self consumption`, `autonomous`, `backup`) — *Primary status & control*
- **`GV1`**: Backup Reserve (%) (`%`)
- **`GV3`**: Storm Mode (`Disabled` / `Enabled`)
- **`GV5`**: Grid Import to battery (`Allowed` / `Not Allowed`)
- **`GV6`**: Grid Export Mode (`PV-only`, `Battery-ok`, `Never`)
- **`GV7`**: EV offgrid charge reserve (%) (`%`)
- **Commands**:
  - `OPMODE`: Set Operating Mode
  - `BACKUPPCT`: Set Backup Reserve (%)
  - `STORMMODE`: Set Storm Mode
  - `GRIDMODE`: Set Grid Operation
  - `import`: Set Grid Import to battery
  - `export`: Set Grid Export Mode
  - `EVCHRGMODE`: Set EV Off-Grid Charge Reserve (%)
  - `UPDATE`: Refresh Parameters

---

## Polling & API Rate Limits

- **shortPoll** (default `60` seconds): Queries critical live status parameters and sends heartbeat to PG3x.
- **longPoll** (default `180` seconds): Queries all metrics, energy history, and parameters.

### Tesla API Limits
- **Powerwall Control Commands**: Tesla Fleet API limits control commands to 5 calls per day per system under standard tiers.
- **Data Requests**: Tesla Fleet API allows up to 100,000 data requests per day per system.

---

## Version History

### Version 0.3.1
- **Hardware-Aware Local Access Detection**: Powerwall hardware model and gateway type are auto-detected (Powerwall 2 vs Powerwall 3 / neop). Local API configuration parameters (`pw_ip_address`, `pw_email`, `pw_customer_pwd`) and setup notice are only presented if the connected Powerwall supports local customer access.
- **Yesterday's Power Summary Updates**:
  - Resolved caching bug preventing yesterday's energy metrics from updating after midnight.
  - Added calendar date-aware cache invalidation (`history_yesterday_date`) and fixed midnight rollover date latching.
  - Fixed typo in local grid export calculation (`yesterdayTotalGeneration`) and aligned yesterday's solar metrics with `tesla_solar_energy_exported`.
  - Added forced yesterday history refresh on manual ISY `UPDATE` command.
  - Fixed zero-event handling for yesterday's backup and EV charging metrics.

### Version 0.3.0
- **Explicit Driver Names**: Added explicit `'name'` attribute definitions to all drivers across all node classes (`CONTROLLER`, `PWSTATUS`, `PWHISTORY`, `PWSETUP`) matching dynamic profiles and NLS definitions.
- **History Node (`PWHISTORY`) Reorganization**:
  - Moved **Home Total Use Today** to **`ST`** for primary status display in IoX admin console and folder trees.
  - Moved **Connected to Tesla / Online** to **`GV0`**.
  - Maintained **`GV8`** as **Home Total Use Today** to preserve symmetrical pairing with **`GV15`** (Home Total Use Yesterday) and existing program compatibility.
  - Eliminated unused `GV1`.
- **Conditional Generator Drivers**: Generator drivers (`GV28` on Status, `GV2` on History) are dynamically omitted when no generator is installed (`is_generator_installed() == False`).
- **Setup Node (`PWSETUP`) Operating Mode on ST**: Set `ST` to Operating Mode, serving as both the status display and command initialization.
- **Online Detection Fix**: Fixed `getTPW_onLine()` so that local polling or cloud activity accurately reports online status, even if the gateway's direct outbound tunnel to Tesla is disconnected.
- **Code Optimization**: Removed obsolete prototype methods and dead initialization loops.

### Version 0.2.6
- Swapped Online and Home Total Use Today in History node.
- Fixed gateway connectivity detection when streaming telemetry is active.
- Refactored controller initialization.

---

## References

- Official Tesla Fleet API: [https://developer.tesla.com/docs/fleet-api#energy-endpoints](https://developer.tesla.com/docs/fleet-api#energy-endpoints)
- Local Gateway API library: [https://github.com/jrester/tesla_powerwall](https://github.com/jrester/tesla_powerwall)
