# udi-TeslaPW  -  for Polyglot v3 

## Tesla PW Node server
# udi-TeslaPW  -  for Polyglot PG3x
## Powerwall Node server

This is an updated version of the Tesla Powerwall Node Server.  It utilizes the official Tesla API now.  At this time there is no cost to use the API but users may be throttled if they poll too often.  Note, there could be a charge to use the API in the future.

The server should be able to support multiple power walls when using cloud (same credentials) - local can only be 1 server at the time.  This has only been tested with a single powerwall setup as 

This node server requires PG3x to run - it will not run on PG3

To install one must configure the region of the server (NA,EU or CN).  If local access is also desired, the relevant parameters must be specified as well 

The following limits exist:

5 call to power wall control per day
100K data requests per power wall system per day 

### Grant access to Tesla API
Once started, the server will require authentication and the user must follow the login request in the web page (from Tesla) and then allow access to data. The following permissions must be granted.
- Energy Product Information
- Energy Product Settings

If permissions need to be updated or changed, log into tesla.com and manage your third party apps.
Note that if you are also using the udiTeslaEV2 node server and you only granted the permissions necessary for that node server, you will probably need to update and grant the additional permissions necessary for this node server.
These settings are in the Tesla website under Account Settings -> Security -> Third Party Apps -> Tesla Plugin for IoX.

There is one main node with overall info.
Each power wall system has it own node with setup and history sub-nodes.
Most of the parameters are the same as previous node, but there have been some updates to allow the use of official API

## Code
The cloud portion of the server uses the official Tesla API (https://developer.tesla.com/docs/fleet-api#energy-endpoints)
The local data is based on API (not official) https://github.com/jrester/tesla_powerwall API - not official Tesla API 


## Installation
To run the node server the user must first configure the data source - from local Powerwall and/ or Tesla Cloud. 

For local access:
Enter IP address and user_email/ password for local and user_email/ password as well as set local_access to True

For cloud access:
Enter region for the power wall (NA, EU or CN) and set cloud_access to True. Save and press Authentication. Grant access as described above. 

## Notes 

shortPoll updates critical parameters (and issues a heartbeat)

longPoll updates all parameters

