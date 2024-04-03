
#!/usr/bin/env python3

### Your external service class
'''
Your external service class can be named anything you want, and the recommended location would be the lib folder.
It would look like this:

External service sample code
Copyright (C) 2023 Universal Devices

MIT License
'''

import json
import requests
import time
#import urllib
from datetime import timedelta, datetime
from tzlocal import get_localzone
#from udi_interface import logging, Custom
#from oauth import OAuth
try:
    import udi_interface
    logging = udi_interface.LOGGER
    Custom = udi_interface.Custom
    ISY = udi_interface.ISY
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
        self.customOauthHandlerDone = False
        self.authendication_done = False
        self.temp_unit = 'C'
        
        self.poly = polyglot

        logging.info('External service connectivity initialized...')

        time.sleep(1)

        #while not self.handleCustomParamsDone:
        #    logging.debug('Waiting for customParams to complete - getAccessToken')
        #    time.sleep(0.2)
        # self.getAccessToken()
    
    # The OAuth class needs to be hooked to these 3 handlers
    def customDataHandler(self, data):
        logging.debug('customDataHandler called')
        #while not self.handleCustomParamsDone:
        #    logging.debug('Waiting for customDataHandler to complete')
        #    time.sleep(1)
        super().customDataHandler(data)
        self.customDataHandlerDone = True
        logging.debug('customDataHandler Finished')

    def customNsHandler(self, key, data):
        logging.debug('customNsHandler called')
        #while not self.customParamsDone():
        #    logging.debug('Waiting for customNsHandler to complete')
        #    time.sleep(1)
        #self.updateOauthConfig()
        super().customNsHandler(key, data)
        self.customNsHandlerDone = True
        logging.debug('customNsHandler Finished')

    def oauthHandler(self, token):
        logging.debug('oauthHandler called')
        while not self.customNsDone():
            logging.debug('Waiting for initilization to complete before oAuth')
            time.sleep(5)
        #logging.debug('oauth Parameters: {}'.format(self.getOauthSettings()))
        super().oauthHandler(token)
        #self.customOauthHandlerDone = True
        #while not self.authendication_done :
        try:
            accessToken = self.getAccessToken()
            logging.debug('oauthHandler {} '.format(accessToken))
            self.authendication_done = True
        except ValueError as err:
            logging.error(' No access token exist - try again : {}'.format(err))
            time.sleep(1)
            self.authendication_done = False

        logging.debug('oauthHandler Finished')

    def customNsDone(self):
        return(self.customNsHandlerDone)
    
    def customDateDone(self):
        return(self.customDataHandlerDone )


    #def customOauthDone(self):
    #    return(self.customOauthHandlerDone )
    # Your service may need to access custom params as well...


   
    def cloud_access(self):
        return(self.cloud_access_enabled)
    

                
    def cloud_initialilze(self, region):
        #self.customParameters.load(userParams)
        #logging.debug('customParamsHandler called {}'.format(userParams))

        oauthSettingsUpdate = {}
        #oauthSettingsUpdate['parameters'] = {}
        oauthSettingsUpdate['token_parameters'] = {}
        # Example for a boolean field

        logging.debug('region {}'.format(self.region))
        oauthSettingsUpdate['scope'] = self.scope 
        oauthSettingsUpdate['auth_endpoint'] = 'https://auth.tesla.com/oauth2/v3/authorize'
        oauthSettingsUpdate['token_endpoint'] = 'https://auth.tesla.com/oauth2/v3/token'
        #oauthSettingsUpdate['redirect_uri'] = 'https://my.isy.io/api/cloudlink/redirect'
        #oauthSettingsUpdate['cloudlink'] = True
        oauthSettingsUpdate['addRedirect'] = True
        #oauthSettingsUpdate['state'] = self.state
        if region.upper() == 'NA':
            endpoint = self.EndpointNA
        elif region.upper() == 'EU':
            endpoint = self.EndpointEU
        elif region.upper() == 'CN':
            endpoint = self.EndpointCN
        else:
            logging.error('Unknow region specified {}'.format(self.region))
            return
           
        self.yourApiEndpoint = endpoint+self.api 
        oauthSettingsUpdate['token_parameters']['audience'] = endpoint
        self.updateOauthSettings(oauthSettingsUpdate)
        time.sleep(0.1)
        logging.debug('getOauthSettings: {}'.format(self.getOauthSettings()))
        #logging.debug('Updated oAuth config 2: {}'.format(temp))
        
        #self.handleCustomParamsDone = True
        #self.poly.Notices.clear()
    
        '''
    def add_to_parameters(self,  key, value):
        #add_to_parameters
        self.customParameters[key] = value

    def check_parameters(self, key, value):
        #check_parameters
        if key in self.customParameters:
            return(self.customParameters[key]  == value)
        else:
            return(False)
        '''
    '''
    def getAccessToken(self):
        # Make sure we have received tokens before attempting to renew
        logging.debug('self.getAccessToken: {}'.format(self._oauthTokens))
        if self._oauthTokens is not None and self._oauthTokens.get('refresh_token'):
            expiry = self._oauthTokens.get('expiry')

            # If expired or expiring in less than 60 seconds, refresh
            if ((expiry is None or datetime.fromisoformat(expiry) - timedelta(seconds=60) < datetime.now())):
                logging.info(f"Access tokens: Token is expired since { expiry }. Initiating refresh.")
                self._oAuthTokensRefresh()
            else:
                logging.info(f"Access tokens: Token is still valid until { expiry }, no need to refresh")

            return self._oauthTokens.get('access_token')
        else:
            raise ValueError('Access token is not available')
    ...

    '''
    def _oAuthTokensRefresh(self):
        logging.debug(f"Refresh token before: { self._oauthTokens }")
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': self._oauthTokens['refresh_token'],
            'client_id': self._oauthConfig['client_id'],
            'client_secret': self._oauthConfig['client_secret']
        }

        if self._oauthConfig['addRedirect']:
            data['redirect_uri'] = 'https://my.isy.io/api/cloudlink/redirect'

        if self._oauthConfig['scope']:
            data['scope'] = self._oauthConfig['scope']

        if self._oauthConfig['token_parameters'] and isinstance(self._oauthConfig['token_parameters'], dict):
            for key, value in self._oauthConfig['token_parameters'].items():
                data[key] = value

        logging.debug(f"Token refresh body { json.dumps(data) }")

        try:
            response = requests.post(self._oauthConfig['token_endpoint'], data=data)
            response.raise_for_status()
            token = response.json()
            logging.info('Refreshing oAuth tokens successfully')
            logging.debug(f"Token refresh result [{ type(token) }]: { token }")
            self._setExpiry(token)
            self._oauthTokens.load(token)
            self.authendication_done = True
            self.poly.Notices.clear()

        except requests.exceptions.HTTPError as error:
            logging.warning(f"Failed to refresh oAuth token: { error } - try Authenticating again")
            self.poly.Notices['auth'] = 'Please initiate authentication - press Authenticate button'
            raise ValueError('Access token is not available')

            # NOTE: If refresh tokens fails, we keep the existing tokens available.
                
        '''
    def try_authendication(self):
        if (self._oauthTokens):  # has been authenticated before 
            try:
                accessToken = self.getAccessToken()
                self.poly.Notices.clear()
                logging.debug('access token (try auth {})'.format(self._oauthTokens))
                return(self._oauthTokens.get('expiry') != None)
            except ValueError as err:
                logging.warning('Access token is not yet available. Please authenticate.')
                self.poly.Notices['auth'] = 'Please initiate authentication  - press authenticate'
                logging.debug('try_authendication oauth error: {}'.format(err))
                return (False)
        else:
            self.poly.Notices['auth'] = 'Please initiate authentication - press authenticate'
            return (False)
        

    def authendicated(self):
        logging.debug('authendicated : {} {}'.format(self._oauthTokens.get('expiry') != None, self._oauthTokens))
        return(self._oauthTokens.get('expiry') != None)
 
    # Call your external service API
    def _callApi(self, method='GET', url=None, body=''):
        # When calling an API, get the access token (it will be refreshed if necessary)
        try:
            accessToken = self.getAccessToken()
            self.poly.Notices.clear()
        except ValueError as err:
            logging.warning('Access token is not yet available. Please authenticate.')
            self.poly.Notices['auth'] = 'Please initiate authentication'
            logging.debug('_callAPI oauth error: {}'.format(err))
            return
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
                response = requests.get(completeUrl, headers=headers, json=body)
            elif method == 'DELETE':
                response = requests.delete(completeUrl, headers=headers)
            elif method == 'PATCH':
                response = requests.patch(completeUrl, headers=headers, json=body)
            elif method == 'POST':
                response = requests.post(completeUrl, headers=headers, json=body)
            elif method == 'PUT':
                response = requests.put(completeUrl, headers=headers)

            response.raise_for_status()
            try:
                return response.json()
            except requests.exceptions.JSONDecodeError:
                return response.text

        except requests.exceptions.HTTPError as error:
            logging.error(f"Call { method } { completeUrl } failed: { error }")
            return None

