
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
        #self.poly.subscribe(self.poly.CUSTOMNS, self.customNsHandler)
        #self.poly.subscribe(self.poly.OAUTH, self.oauthHandler)
        self.poly = polyglot

        logging.info('External service connectivity initialized...')

        #time.sleep(1)

        #while not self.handleCustomParamsDone:
        #    logging.debug('Waiting for customParams to complete - getAccessToken')
        #    time.sleep(0.2)
        # self.getAccessToken()
    
    # The OAuth class needs to be hooked to these 3 handlers
    
    def customDataHandler(self, data):
        logging.debug('customDataHandler called {}'.format(data))
        #while not self.handleCustomParamsDone:
        #    logging.debug('Waiting for customDataHandler to complete')
        #    time.sleep(1)       
        logging.debug('customDataHandler result: {}'.format(super().customDataHandler(data)))
        self.customDataHandlerDone = True
        logging.debug('customDataHandler Finished')
    '''    

    def customDataHandler(self, data):
        if data.get('token'):
            logging.info('Migrating tokens to the new version')
            # Save token data to the new oAuthTokens custom
            Custom(self.poly, 'oauthTokens').load(data['token'], True)

            # Save customdata without the key 'token'
            newData = { key: value for key, value in data.items() if key != 'token' }
            Custom(self.poly, 'customdata').load(newData, True)
            
            # Continue processing as if it was in the right place
            self.customNsHandler('oauthTokens', data['token'])
    '''
        
    def customNsHandler(self, key, data):
        logging.debug('customNsHandler called {} {}'.format(key, data))
        #while not self.customParamsDone():
        #    logging.debug('Waiting for customNsHandler to complete')
        #    time.sleep(1)
        #self.updateOauthConfig()
        logging.debug('customerNSHandler results: {}'.format(super().customNsHandler(key, data)))
        if key == 'oauthTokens': # stored oauthToken values processed
            self.customNsHandlerDone = True
        logging.debug('customNsHandler Finished')

    def oauthHandler(self, token):
        logging.debug('oauthHandler called')
        #while not self.customNsDone():
        #    logging.debug('Waiting for initilization to complete before oAuth')
        #    time.sleep(5)
        #logging.debug('oauth Parameters: {}'.format(self.getOauthSettings()))
        logging.debug('oauthHandler result: {}'.format(super().oauthHandler(token)))
        self.oauthHandlerCalled = True
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
        return(self.customNsHandlerDone)
    
    def customDateDone(self):
        return(self.customDataHandlerDone )


    #def customOauthDone(self):
    #    return(self.customOauthHandlerDone )
    # Your service may need to access custom params as well...


   
    def cloud_access(self):
        return(self.cloud_access_enabled)
    

                
    def cloud_set_region(self, region):
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
        #time.sleep(0.1)
        logging.debug('getOauthSettings: {}'.format(self.getOauthSettings()))
        #logging.debug('Updated oAuth config 2: {}'.format(temp))
        #self.handleCustomParamsDone = True
        #self.poly.Notices.clear()



    def authenticated(self):
        #self.apiLock.acquire()
        logging.debug('authenticated : {} {}'.format(self._oauthTokens.get('expiry') != None, self._oauthTokens))
        #if not self._oauthTokens:
        #   time.sleep(1)
        #   logging.debug('Waiting for system to initialize')
        #   self.poly.Notices['auth'] = 'Please initiate authentication'
        try:
            if 'expiry' not in self._oauthTokens:            
                self.getAccessToken()
                #time.sleep(2)
            #self.apiLock.release()
            return(self._oauthTokens.get('expiry') != None)
        except ValueError as err:
            logging.warning('Access token is not yet available. Please authenticate.')
            self.poly.Notices['auth'] = 'Please initiate authentication'
            logging.debug('_callAPI oauth error: {}'.format(err))
            return (False)

        #return('expiry' in self._oauthTokens)
 

    # Call your external service API
    def _callApi(self, method='GET', url=None, body=''):
        # When calling an API, get the access token (it will be refreshed if necessary)
        #self.apiLock.acquire()
        try:
            #self._oAuthTokensRefresh()  #force refresh
            accessToken = self.getAccessToken()
            #refresh_token = self._oauthTokens.get('refresh_token')
            #logging.debug('call api tokens: {} {}'.format(refresh_token, accessToken))
            self.poly.Notices.clear()
        except ValueError as err:
            logging.warning('Access token is not yet available. Please authenticate.')
            self.poly.Notices['auth'] = 'Please initiate authentication'
            logging.debug('_callAPI oauth error: {}'.format(err))
            accessToken = None
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
            #self.apiLock.release()
            
            try:
                return response.json()
            except requests.exceptions.JSONDecodeError:
                return response.text

        except requests.exceptions.HTTPError as error:
            logging.error(f"Call { method } { completeUrl } failed: { error }")
            #self.apiLock.release()
            return None
        
