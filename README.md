# udi-TeslaPW - Polyglot PG3x Node Server for Tesla Powerwall

This is an updated version of the Tesla Powerwall Node Server for Universal Devices eisy / Polisy running **Polyglot PG3x** (v3.x). It integrates with the official **Tesla Fleet API** for cloud monitoring and control, with optional local LAN gateway telemetry for Powerwall 2 systems.

## Key Features

- **Official Tesla Fleet API Integration**: Direct OAuth authentication and cloud telemetry/control via Tesla's Fleet API.
- **Zero-Config Cloud Discovery**: Automatically discovers your account region (NA, EU, or CN) on initial authentication.
- **Optional Local LAN Telemetry (Powerwall 2)**: Direct high-speed local polling from the Powerwall Gateway API when configured, with automatic fallback to cloud telemetry.
- **Dynamic Node Profiles**: Sub-nodes and driver sets automatically adapt based on your system configuration (e.g., hiding generator drivers if no generator is installed).
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

The node server creates a primary controller node, plus a set of nodes for each detected Powerwall energy site:

### 1. Controller Node (`CONTROLLER` - Tesla PowerWall Info)
Main node server status and connectivity monitor.
- **`ST`**: Controller Up (`Up` / `Down`)
- **`GV2`**: Connected to Tesla Power Wall (`Not Connected` / `Connected`)
- **`GV3`**: Consecutive Missed LongPolls
- **`GV4`**: Connection Status (`No Connection`, `Cloud only`, `Local only`, `Local and Cloud`)
- **Commands**:
  - `UPDATE`: Forces an immediate query and update of system data.

### 2. Status Node (`PWSTATUS` - Power Wall Status)
Live status, instantaneous power flows, and current operation modes.
- **`ST`**: Connected to Tesla / Online (`offline` / `online`)
- **`GV0`**: Remaining Battery Charge (`%`)
- **`GV1`**: Instantaneous Solar Export (`kW`)
- **`GV2`**: Instantaneous Battery Export (`kW`)
- **`GV3`**: Instantaneous Home Load (`kW`)
- **`GV4`**: Instantaneous Grid Import (`kW`)
- **`GV5`**: Operating Mode (`backup`, `self consumption`, `autonomous`, `site control`)
- **`GV6`**: Grid Status (`on grid`, `islanded ready`, `islanded`, `transition to grid`)
- **`GV7`**: Grid Services Active (`Disabled` / `Enabled`)
- **`GV8`**: Home Total Use Today (`kWh`)
- **`GV9`**: Solar Export Today (`kWh`)
- **`GV10`**: Battery Export Today (`kWh`)
- **`GV11`**: Battery Import Today (`kWh`)
- **`GV12`**: Grid Export Today (`kWh`)
- **`GV13`**: Grid Import Today (`kWh`)
- **`GV14`**: Grid / House Net Use Today (`kWh`)
- **`GV28`**: Generator Today (`kWh`) *(conditionally displayed only if a generator is installed)*
- **`TIME`**: Last Update Timestamp
- **Commands**: `UPDATE`

### 3. Usage History Node (`PWHISTORY` - Power Wall History)
Daily and historical energy consumption, backup events, and EV charging data.
- **`ST`**: Home Total Use Today (`kWh`) — *Primary status shown in IoX folder tree views*
- **`GV0`**: Connected to Tesla / Online (`offline` / `online`)
- **`GV8`**: Home Total Use Today (`kWh`) — *Maintained for symmetry with GV15*
- **`GV9`**: Solar Export Today (`kWh`)
- **`GV10`**: Battery Export Today (`kWh`)
- **`GV11`**: Battery Import Today (`kWh`)
- **`GV12`**: Grid Export Today (`kWh`)
- **`GV13`**: Grid Import Today (`kWh`)
- **`GV14`**: Grid / House Net Use Today (`kWh`)
- **`GV15`**: Home Total Use Yesterday (`kWh`)
- **`GV16`**: Solar Export Yesterday (`kWh`)
- **`GV17`**: Battery Export Yesterday (`kWh`)
- **`GV18`**: Battery Import Yesterday (`kWh`)
- **`GV19`**: Grid Export Yesterday (`kWh`)
- **`GV20`**: Grid Import Yesterday (`kWh`)
- **`GV21`**: Grid / House Net Use Yesterday (`kWh`)
- **`GV22`**: Today Number of Backup Events
- **`GV23`**: Today Backup Event Duration (seconds)
- **`GV24`**: Yesterday Number of Backup Events
- **`GV25`**: Yesterday Backup Event Duration (seconds)
- **`GV26`**: Today EV Charge Energy (`kWh`)
- **`GV27`**: Today EV Charge Duration (seconds)
- **`GV28`**: Yesterday EV Charge Energy (`kWh`)
- **`GV29`**: Yesterday EV Charge Duration (seconds)
- **`GV2`**: Generator Yesterday (`kWh`) *(conditionally displayed only if a generator is installed)*
- **Commands**: `UPDATE`

### 4. Control Parameters Node (`PWSETUP` - Power Wall Control Parameters)
Allows controlling Powerwall operating parameters from IoX / ISY programs and admin console.
- **`ST`**: Operating Mode (`self consumption`, `autonomous`, `backup`) — *Primary status & control*
- **`GV1`**: Backup Reserve Percentage (`%`)
- **`GV3`**: Storm Mode (`Disabled` / `Enabled`)
- **`GV5`**: Grid Import to Battery (`Allowed` / `Not Allowed`)
- **`GV6`**: Grid Export Mode (`PV-only`, `Battery-ok`, `Never`)
- **`GV7`**: EV Off-Grid Charge Reserve (`%`)
- **Commands**:
  - `OPMODE`: Set Operating Mode
  - `BACKUPPCT`: Set Backup Reserve (%)
  - `STORMMODE`: Set Storm Mode
  - `GRIDMODE`: Set Grid Operation
  - `import`: Set Grid Import to Battery
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

## References

- Official Tesla Fleet API: [https://developer.tesla.com/docs/fleet-api#energy-endpoints](https://developer.tesla.com/docs/fleet-api#energy-endpoints)
- Local Gateway API library: [https://github.com/jrester/tesla_powerwall](https://github.com/jrester/tesla_powerwall)
