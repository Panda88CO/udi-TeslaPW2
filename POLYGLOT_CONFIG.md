# teslaPW

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

If these parameters are present, the node server tests local connectivity on startup and uses local LAN telemetry if available. If local access is unsupported or fails, it gracefully falls back to Cloud access without interruption.

If additional functionality is desired contact the author through github - https://github.com/Panda88CO/udi-TeslaPW

Enjoy!
