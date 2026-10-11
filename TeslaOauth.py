
#!/usr/bin/env python3

### Your external service class
'''
Your external service class can be named anything you want, and the recommended location would be the lib folder.
It would look like this:

External service sample code
Copyright (C) 2023 Universal Devices

MIT License
'''

import requests
import time
from threading import Lock
from datetime import timedelta, datetime
from tzlocal import get_localzone

try:
    import udi_interface
    logging = udi_interface.LOGGER
#    Custom = udi_interface.Custom
#    ISY = udi_interface.ISY
except ImportError:
    import logging
    logging.basicConfig(level=30)


#from udi_interface import logging, Custom, OAuth, ISY
#logging = udi_interface.logging
#Custom = udi_interface.Custom
#ISY = udi_interface.ISY



# Implements the API calls to your external service
# It inherits the OAuth class
class teslaAccess(udi_interface.OAuth):
    yourApiEndpoint = 'https://fleet-api.prd.na.vn.cloud.tesla.com'

    def __init__(self, polyglot, scope):
        super().__init__(polyglot)
        logging.info('OAuth initializing')
        self.poly = polyglot
        self.scope = scope
        #self.customParameters = Custom(self.poly, 'customparams')
        #self.scope_str = None
        self.EndpointNA= 'https://fleet-api.prd.na.vn.cloud.tesla.com'
        self.EndpointEU= 'https://fleet-api.prd.eu.vn.cloud.tesla.com'
        self.EndpointCN= 'https://fleet-api.prd.cn.vn.cloud.tesla.cn'
        self.api  = '/api/1'
        #self.local_access_enabled = False
        self.cloud_access_enabled = False
        #self.state = secrets.token_hex(16)
        self.region = ''
        #self.handleCustomParamsDone = False
        #self.customerDataHandlerDone = False
        self.customNsHandlerDone = False
        self.oauthHandlerCalled = False
        self.customDataHandlerDone = False
        self.authendication_done = False
        self.apiLock = Lock()
        self.temp_unit = 'C'
        self.timeout = (5.0, 15.0)
        self._session = requests.Session() if hasattr(requests, 'Session') else requests
        #self.poly.subscribe(self.poly.CUSTOMNS, self.customNsHandler)
        #self.poly.subscribe(self.poly.OAUTH, self.oauthHandler)
        self.poly = polyglot

        logging.info('External service connectivity initialized...')

    def close(self):
        try:
            if hasattr(self, '_session') and hasattr(self._session, 'close'):
                self._session.close()
        except Exception as e:
            logging.debug('Error closing cloud session: {}'.format(e))

        #time.sleep(1)

        #while not self.handleCustomParamsDone:
        #    logging.debug('Waiting for customParams to complete - getAccessToken')
        #    time.sleep(0.2)
        # self.getAccessToken()
    
    # The OAuth class needs to be hooked to these 3 handlers
    
    def customDataHandler(self, data):
        logging.debug('customDataHandler called {}'.format(data))
        if isinstance(data, dict) and data.get('token'):
            logging.info('Migrating tokens to the new version')
            # Save token data to the new oAuthTokens custom
            Custom(self.poly, 'oauthTokens').load(data['token'], True)

            # Save customdata without the key 'token'
            newData = { key: value for key, value in data.items() if key != 'token' }
            Custom(self.poly, 'customdata').load(newData, True)
            
            # Continue processing as if it was in the right place
            self.customNsHandler('oauthTokens', data['token'])
        self.customDataHandlerDone = True
        logging.debug('customDataHandler Finished')
        
    def customNsHandler(self, key, data):
        logging.debug('customNsHandler called {} {}'.format(key, data))
        #while not self.customParamsDone():
        #    logging.debug('Waiting for customNsHandler to complete')
        #    time.sleep(1)
        #self.updateOauthConfig()
        logging.debug('customerNSHandler results: {}'.format(super().customNsHandler(key, data)))
        if key in ['oauth', 'oauthTokens']: # stored oauth / oauthToken values processed
            self.customNsHandlerDone = True
        if key == 'oauthTokens' and isinstance(data, dict):
            # If we received stored tokens with access_token or refresh_token, ensure expiry is set if missing
            if 'expiry' not in data and 'expires_in' in data:
                try:
                    self._setExpiry(data)
                    self._oauthTokens.load(data, save=True)
                except Exception as ex:
                    logging.debug(f'Could not set expiry: {ex}')
            # Clear authentication notice if we have valid tokens loaded from DB
            if data.get('access_token') or data.get('refresh_token'):
                if hasattr(self, 'poly') and hasattr(self.poly, 'Notices') and 'auth' in self.poly.Notices:
                    self.poly.Notices.delete('auth')
        logging.debug('customNsHandler Finished')

    def oauthHandler(self, token):
        logging.debug('oauthHandler called')
        #while not self.customNsDone():
        #    logging.debug('Waiting for initilization to complete before oAuth')
        #    time.sleep(5)
        #logging.debug('oauth Parameters: {}'.format(self.getOauthSettings()))
        logging.debug('oauthHandler result: {}'.format(super().oauthHandler(token)))
        self.oauthHandlerCalled = True
        if hasattr(self, 'poly') and hasattr(self.poly, 'Notices') and 'auth' in self.poly.Notices:
            self.poly.Notices.delete('auth')
        #while not self.authendication_done :
        #time.sleep(2)
        '''
        try:
            accessToken = self.getAccessToken()
            logging.debug('oauthHandler {} '.format(accessToken))
            self.authendication_done = True
        except ValueError as err:
            logging.error(' No access token exist - try again : {}'.format(err))
            time.sleep(1)
            self.authendication_done = False

        logging.debug('oauthHandler Finished')
        '''
        return(True)
    
    def oauthHandlerRun(self):
        return(self.oauthHandlerCalled)
    def customNsDone(self):
        return self.customNsHandlerDone or getattr(self, '_oauthConfigInitialized', False)
    
    def customDataDone(self):
        return self.customDataHandlerDone

    def customDateDone(self):
        return self.customDataHandlerDone


    #def customOauthDone(self):
    #    return(self.customOauthHandlerDone )
    # Your service may need to access custom params as well...


   
    def cloud_access(self):
        return(self.cloud_access_enabled)
    

                
    def cloud_set_region(self, region):
        oauthSettingsUpdate = {}
        oauthSettingsUpdate['token_parameters'] = {}

        if not region:
            region = 'NA'
        self.region = region.upper()
        logging.debug('cloud_set_region: {}'.format(self.region))
        oauthSettingsUpdate['scope'] = self.scope 
        oauthSettingsUpdate['auth_endpoint'] = 'https://auth.tesla.com/oauth2/v3/authorize'
        oauthSettingsUpdate['token_endpoint'] = 'https://fleet-auth.prd.vn.cloud.tesla.com/oauth2/v3/token'
        oauthSettingsUpdate['addRedirect'] = True

        if self.region == 'NA':
            endpoint = self.EndpointNA
        elif self.region == 'EU':
            endpoint = self.EndpointEU
        elif self.region == 'CN':
            endpoint = self.EndpointCN
        else:
            logging.error('Unknown region specified: {}'.format(self.region))
            return
           
        self.yourApiEndpoint = endpoint + self.api 
        oauthSettingsUpdate['token_parameters']['audience'] = endpoint
        self.updateOauthSettings(oauthSettingsUpdate)
        logging.debug('getOauthSettings: {}'.format(self.getOauthSettings()))

    def discover_user_region(self):
        """Auto-discovers the user's registered Fleet API region via GET /api/1/users/region."""
        try:
            res = self._callApi('GET', '/users/region')
            if res and isinstance(res, dict) and 'response' in res:
                user_info = res['response']
                detected_region = user_info.get('region', '').upper()
                base_url = user_info.get('fleet_api_base_url')
                logging.info(f"Tesla Fleet API auto-detected user region: {detected_region} (base_url: {base_url})")
                if base_url:
                    self.yourApiEndpoint = base_url.rstrip('/') + self.api
                if detected_region in ['NA', 'EU', 'CN'] and detected_region != self.region:
                    self.region = detected_region
                    self.cloud_set_region(self.region)
                return self.region
        except Exception as e:
            logging.warning(f"Unable to auto-detect user region from /users/region: {e}")
        return self.region



    def authenticated(self):
        logging.debug('authenticated : tokens={}'.format(self._oauthTokens))
        if not self._oauthTokens or not isinstance(self._oauthTokens, dict):
            return False

        has_tokens = bool(self._oauthTokens.get('access_token') or self._oauthTokens.get('refresh_token'))
        if not has_tokens:
            if hasattr(self, 'poly') and hasattr(self.poly, 'Notices'):
                self.poly.Notices['auth'] = 'Please initiate authentication - press Authenticate button'
            return False

        # If expiry is not in tokens, populate it to avoid refresh errors
        if 'expiry' not in self._oauthTokens:
            if 'expires_in' in self._oauthTokens:
                try:
                    self._setExpiry(self._oauthTokens)
                except Exception:
                    pass
            elif self._oauthTokens.get('access_token'):
                self._oauthTokens['expiry'] = (datetime.now() + timedelta(seconds=28800)).isoformat()

        try:
            token = self.getAccessToken()
            is_auth = bool(token)
            if is_auth:
                if hasattr(self, 'poly') and hasattr(self.poly, 'Notices') and 'auth' in self.poly.Notices:
                    self.poly.Notices.delete('auth')
            else:
                if hasattr(self, 'poly') and hasattr(self.poly, 'Notices'):
                    self.poly.Notices['auth'] = 'Please initiate authentication - press Authenticate button'
            return is_auth
        except ValueError as err:
            if self._oauthTokens.get('access_token'):
                if hasattr(self, 'poly') and hasattr(self.poly, 'Notices') and 'auth' in self.poly.Notices:
                    self.poly.Notices.delete('auth')
                return True
            logging.warning('Access token is not yet available. Please authenticate.')
            if hasattr(self, 'poly') and hasattr(self.poly, 'Notices'):
                self.poly.Notices['auth'] = 'Please initiate authentication - press Authenticate button'
            logging.debug('_callAPI oauth error: {}'.format(err))
            return False

    # Call your external service API
    def _callApi(self, method='GET', url=None, body=''):
        # When calling an API, get the access token (it will be refreshed if necessary)
        try:
            accessToken = self.getAccessToken()
            if hasattr(self, 'poly') and hasattr(self.poly, 'Notices') and 'auth' in self.poly.Notices:
                self.poly.Notices.delete('auth')
        except ValueError as err:
            logging.warning('Access token is not yet available. Please authenticate.')
            if hasattr(self, 'poly') and hasattr(self.poly, 'Notices'):
                self.poly.Notices['auth'] = 'Please initiate authentication - press Authenticate button'
            logging.debug('_callAPI oauth error: {}'.format(err))
            accessToken = None
            return None
        if accessToken is None:
            logging.error('Access token is not available')
            return None

        if url is None:
            logging.error('url is required')
            return None

        completeUrl = self.yourApiEndpoint + url

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer { accessToken }'
        }

        if method in [ 'PATCH', 'POST'] and body is None:
            logging.error(f"body is required when using { method } { completeUrl }")
        logging.debug(' call info url={}, header {}, body ={}'.format(completeUrl, headers, body))

        try:
            if method == 'GET':
                response = self._session.get(completeUrl, headers=headers, json=body, timeout=self.timeout)
            elif method == 'DELETE':
                response = self._session.delete(completeUrl, headers=headers, timeout=self.timeout)
            elif method == 'PATCH':
                response = self._session.patch(completeUrl, headers=headers, json=body, timeout=self.timeout)
            elif method == 'POST':
                response = self._session.post(completeUrl, headers=headers, json=body, timeout=self.timeout)
            elif method == 'PUT':
                response = self._session.put(completeUrl, headers=headers, timeout=self.timeout)

            response.raise_for_status()

            if hasattr(self, 'poly') and hasattr(self.poly, 'Notices'):
                if 'rate_limit' in self.poly.Notices:
                    self.poly.Notices.delete('rate_limit')
                if 'region_error' in self.poly.Notices:
                    self.poly.Notices.delete('region_error')
            
            try:
                return response.json()
            except (requests.exceptions.JSONDecodeError, ValueError):
                return response.text

        except requests.exceptions.HTTPError as error:
            status_code = error.response.status_code if error.response is not None else None
            logging.error(f"Call { method } { completeUrl } failed: { error } (Status: { status_code })")
            
            if status_code == 429:
                retry_after = 'unknown'
                if error.response is not None and hasattr(error.response, 'headers') and error.response.headers:
                    retry_after = error.response.headers.get('Retry-After', 'unknown')
                logging.warning(f"Tesla Fleet API rate limit reached (429 Too Many Requests). Retry-After: {retry_after}s.")
                if hasattr(self, 'poly') and hasattr(self.poly, 'Notices'):
                    self.poly.Notices['rate_limit'] = f"Tesla API rate limit reached. Backing off (Retry-After: {retry_after}s)."
                return None
            elif status_code == 412:
                logging.warning(f"Tesla Fleet API Precondition Failed (412). The requested site may belong to a different region than '{self.region}'.")
                if hasattr(self, 'poly') and hasattr(self.poly, 'Notices'):
                    self.poly.Notices['region_error'] = f"Tesla API 412 Precondition Failed. Check region setting ({self.region})."
                return None
            elif status_code == 401:
                logging.info("Received 401 Unauthorized. Attempting token refresh...")
                try:
                    self._oAuthTokensRefresh()
                    new_token = self._oauthTokens.get('access_token') if isinstance(self._oauthTokens, dict) else None
                    if new_token and new_token != accessToken:
                        headers['Authorization'] = f'Bearer {new_token}'
                        logging.info("Retrying API call with refreshed token...")
                        if method == 'GET':
                            retry_resp = self._session.get(completeUrl, headers=headers, json=body, timeout=self.timeout)
                        elif method == 'DELETE':
                            retry_resp = self._session.delete(completeUrl, headers=headers, timeout=self.timeout)
                        elif method == 'PATCH':
                            retry_resp = self._session.patch(completeUrl, headers=headers, json=body, timeout=self.timeout)
                        elif method == 'POST':
                            retry_resp = self._session.post(completeUrl, headers=headers, json=body, timeout=self.timeout)
                        elif method == 'PUT':
                            retry_resp = self._session.put(completeUrl, headers=headers, timeout=self.timeout)
                        retry_resp.raise_for_status()
                        if hasattr(self, 'poly') and hasattr(self.poly, 'Notices'):
                            if 'rate_limit' in self.poly.Notices:
                                self.poly.Notices.delete('rate_limit')
                            if 'region_error' in self.poly.Notices:
                                self.poly.Notices.delete('region_error')
                        try:
                            return retry_resp.json()
                        except (requests.exceptions.JSONDecodeError, ValueError):
                            return retry_resp.text
                except Exception as refresh_err:
                    logging.warning(f"Failed to refresh/retry after 401: {refresh_err}")
                    if hasattr(self, 'poly') and hasattr(self.poly, 'Notices'):
                        self.poly.Notices['auth'] = 'Please initiate authentication - press Authenticate button'
            return None
        except requests.exceptions.Timeout as error:
            logging.error(f"Call { method } { completeUrl } timed out after {self.timeout}s: {error}")
            return None
        except requests.exceptions.ConnectionError as error:
            logging.error(f"Call { method } { completeUrl } connection error: {error}")
            return None
        except requests.exceptions.RequestException as error:
            logging.error(f"Call { method } { completeUrl } network error: {error}")
            return None
        
