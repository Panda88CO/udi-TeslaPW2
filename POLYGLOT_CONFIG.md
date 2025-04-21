# teslaPW

## Installation
For local access to PowerWall the local IP address (LOCAL_IP_ADDRESS) along with login  (LOCAL_USER_EMAIL) and password (LOCAL_USER_PASSWORD) must be added in configuration

It may be necessary to power cycle (turn power wall on and off using the switch on the local power wall) - 

Cloud access is now accessible through the node server directly.
For cloud access enter region for the Powerwall (NA, EU or CN) and set cloud_access to True. Save and press Authentication. Grant access as described below. 

After making the cloud configuration, click the authentication button.  The authentication will redirect to your Tesla login through the Tesla website.  User must grant node server access to data.  Please grant the following permissions:
- Energy Product Information
- Energy Product Settings

After restarting the service, a status node is created for each PowerWall registered in the user account.  Sub-nodes are created for each Powerwall addressing Setup parameters and Usage history.
There is also a node representing the overall configuration and health of the node server.

## Notes
shortPoll updates critical parameters (and issues a heartbeat)

longPoll updates all parameters

If additional functionality is desired contact the author through github - https://github.com/Panda88CO/udi-TeslaPW

Enjoy


