
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
import json
import urllib.parse
#from udi_interface import LOGGER, Custom
from oauth import OAuth
try:
    import udi_interface
    logging = udi_interface.LOGGER
    Custom = udi_interface.Custom
except ImportError:
    import logging
    logging.basicConfig(level=logging.DEBUG)

from datetime import timedelta, datetime

# Implements the API calls to your external service
# It inherits the OAuth class
class NetatmoCloud(object):
   
    def dummy_read(self):
        file = open("token.json", "r")
        self.token = json.load(file)
        file.close()

        file2 = open("client_ID.txt", 'r')
        self.client_ID  = file2.read()
        file2.close()
        file2 = open("client_SEC.txt", 'r')
        self.client_SECRET = file2.read()
        file2.close()

    def __init__(self):
        #super().__init__(polyglot)
        self.scope_str = None
        self.apiEndpoint = 'https://api.netatmo.com'
        self.client_ID = None
        self.client_SECRET = None
        self.token = None
        self.netatmo_systems = {}
        self.dummy_read() #emulate oauth
        self.scope = None
        self.customData = None
        self.homes_list = {}
        #self.module_list = {}
        #self.token= token
        #self.client_ID = client_id
        #self.client_SECRET = client_secret
        self.token_endpoint = 'https://api.netatmo.com/oauth2/token'
        self.yourApiEndpoint = 'https://api.netatmo.com/api'

        self.scopeList = ['read_station', 'write_station', 'read_magellan', 'write_magellan', 'read_bubendorff', 'write_bubendorff', 'read_smarther', 'write_smarther', 'read_thermostat','write_thermostat', 'read+_camera', 'write_camera', 'access_camera', 'read_boorbell', 'access_doorbell',
             'read_mx', 'write_mx', 'read_presence', 'write_presence', 'access_presence', 'read_homecoach', 'read_carbonmonoxidedetector', 'read_smokedetector', 'read_mhs1', 'write_mhs1']

        #self.poly = polyglot
        #self.customParams = Custom(polyglot, 'customparams')
        self.getAccessToken()
        logging.info('External service connectivity initialized...')
        #logging.debug('oauth : {}'.format(self.oauthConfig))
        time.sleep(1)
    
    # The OAuth class needs to be hooked to these 3 handlers
    def customDataHandler(self, data):
        super()._customDataHandler(data)

    def customNsHandler(self, key, data):
        super()._customNsHandler(key, data)

    def oauthHandler(self, token):
        logging.debug('oauthHandler')
        self.updateOauthConfig()
        super()._oauthHandler(token)
    
    def refresh_token(self):
        logging.debug('checking token for refresh')
    

    # Your service may need to access custom params as well...
    def customParamsHandler(self, data):
        self.customParams.load(data)
        logging.debug('customParamsHandler called')
        # Example for a boolean field
        if 'clientID' in self.customParams:
            self.client_ID = self.customParams['clientID'] 
            #self.addOauthParameter('client_id',self.client_ID )
            #self.oauthConfig['client_id'] =  self.client_ID
        else:
            self.customParams['clientID'] = 'enter client_id'
            self.client_ID = None
            
        if 'clientSecret' in self.customParams:
            self.client_SECRET = self.customParams['clientSecret'] 
            #self.addOauthParameter('client_secret',self.client_SECRET )
            #self.oauthConfig['client_secret'] =  self.client_SECRET
        else:
            self.customParams['clientSecret'] = 'enter client_secret'
            self.client_SECRET = None
            
        if 'scope' in self.customParams:
            temp = self.customParams['scope'] 
            temp1 = temp.split()
            self.scope_str = ''
            for net_scope in temp1:
                if net_scope in self.scopeList:
                    self.scope_str = self.scope_str + ' ' + net_scope
                else:
                    logging.error('Unknown scope provide {} - removed '.format(net_scope))
            self.scope = self.scope_str.split()
            
            attempts = 0
            while not self.customData and attempts <3:
                attempts = attempts + 1
                time.sleep(1)

            if self.customData:
                if 'scope' in self.customData:
                    if self.scope_str != self.customData['scope']:
                       #scope changed - we need to generate a new token/refresh token
                       logging.debug('scope has changed - need to get new token')
                       self.poly.Notices['auth'] = 'Please initiate authentication - scope has changed'
                       self.customData['scope'] = self.scope_str
                else: 
                    if self.oauthConfig['client_id'] is None or self.oauthConfig['client_secret'] is None:
                        self.updateOauthConfig()    
                    
                    self.poly.Notices['auth'] = 'Please initiate authentication - scope has changed'
                    self.customData['scope'] = self.scope_str


            #self.addOauthParameter('scope',self.scope_str )
            #self.oauthConfig['scope'] = self.scope_str
            logging.debug('Following scopes are selected : {}'.format(self.scope_str))
        else:
            self.customParams['scope'] = 'enter desired scopes space separated'
            self.scope_str = ""


        if 'refresh_token' in self.customParams:
            if self.customParams['refresh_token'] is not None and self.customParams['refresh_token'] != "":
                self.customData.token['refresh_token'] = self.customParams['refresh_token']


        self.updateOauthConfig()
        #self.myParamBoolean = ('myParam' in self.customParams and self.customParams['myParam'].lower() == 'true')
        #logging.info(f"My param boolean: { self.myParamBoolean }")
        
    

    def process_homes_data(self, net_system):
        homes_list = {}
        for home in range(0, len(net_system['homes'])):
            tmp = net_system['homes'][home]
            homes_list[tmp['id']]= {}
            homes_list[tmp['id']]['name']= tmp['name']
            homes_list[tmp['id']]['modules'] = {}
            homes_list[tmp['id']]['module_types'] = []
            if 'modules' in tmp:
                for mod in range(0,len(tmp['modules'])):
                    homes_list[tmp['id']]['modules'][tmp['modules'][mod]['id']] = tmp['modules'][mod]
                    homes_list[tmp['id']]['module_types'].append( tmp['modules'][mod]['type'] )
        return(homes_list)



    def get_homes_info(self):
        logging.debug('get_home_info')
        api_str = '/homesdata'
        temp = self._callApi('GET', api_str )
        self.netatmo_systems = temp['body']
        logging.debug(self.netatmo_systems)
        self.homes_list = self.process_homes_data(self.netatmo_systems)
        return(self.homes_list)


    def get_home_status(self, home_id):
        status = {}
        logging.debug('get_home_status')
        try:
            if home_id:
                home_id_str = urllib.parse.quote_plus(home_id )
                api_str = '/homestatus?home_id='+str(home_id_str)


            tmp = self._callApi('GET', api_str)
            if tmp:
                tmp = tmp['body']
                if 'errors' not in tmp:
                    tmp = tmp['home']
                    status[home_id] = home_id #tmp['body']['body']['home']
                    if 'modules' in tmp:
                        status['modules'] = {}
                        status['module_types'] = []
                        for mod in range(0,len(tmp['modules'])):
                            status['modules'][tmp['modules'][mod]['id']]= tmp['modules'][mod]
                            status['module_types'].append(tmp['modules'][mod]['type'])
                    logging.debug(status)
                else:
                    status['error'] = tmp['error']

                return(status)
        except Exception as e:
            logging.error('Error get hiome status : {}'.format(e))

    def get_modules(self, home_id):
        '''get_modules'''
        logging.debug('get_modules')
        if home_id in self.homes_list:
            # Find relevan modules
            return(self.homes_list[home_id]['modules'])
        
    def get_module_types(self, home_id):
        '''get_module_types'''
        if home_id in self.homes_list:
            return(self.homes_list[home_id]['module_types'])

    def get_home_name(self, home_id):
        '''get_home_name'''
        if home_id in self.homes_list:
            return(self.homes_list[home_id]['name'])

    def get_modules_present(self, home_id):
        '''get_modules_present'''
        logging.debug('get_modules_present')
        modules = {}
        if home_id in self.homes_list:
            for tmp in range(0,len(self.homes_list[home_id]['modules'])):
                modules[tmp[id]] = tmp
        return(modules)
    
    def get_sub_modules(self, home_id, main_module_id):
        '''get_sub_modules'''
        logging.debug('get_sub_modules')
        if home_id in  self.homes_list:
            if main_module_id in self.homes_list[home_id]['modules']:
                if 'modules_bridged' in self.homes_list[home_id]['modules'][main_module_id]:
                    return(self.homes_list[home_id]['modules'][main_module_id]['modules_bridged'])

    def get_module_info(self, home_id, module_id):
        '''get_module_info'''
        logging.debug('get_module_info')
        if home_id in  self.homes_list:
            if module_id in self.homes_list[home_id]['modules']:
                return(self.homes_list[home_id]['modules'][module_id])


    def _get_modules(self, home_id, mod_type_lst):
        '''get list of weather modules of type attached to house_id'''
        try:
            mod_dict = {}
            if home_id in self.homes_list:
               for module in self.homes_list[home_id]['modules']:
                    if self.homes_list[home_id]['modules'][module]['type'] in mod_type_lst:
                        mod_dict[module] = {}
                        if 'name' in  self.homes_list[home_id]['modules'][module]:
                            mod_dict[module]['name'] = self.homes_list[home_id]['modules'][module]['name']
                        else:
                            mod_dict[module]['name'] = self.homes_list[home_id]['modules'][module]['id']
                    


                    
            else:
                logging.error('No data found for {} {}'.format(home_id, mod_type_lst))
            return(mod_dict)
    
        except Exception as e:
            logging.error('Exception : {}'.format(e))
            return(None)
            
    
    

    # Call your external service API
    def _callApi(self, method='GET', url=None, body=None):
        # When calling an API, get the access token (it will be refreshed if necessary)
        #$Content_Type = "application/x-www-form-urlencoded;charset=UTF-8";
        accessToken = self.getAccessToken()

        if accessToken is None:
            logging.error('Access token is not available')
            return None

        if url is None:
            logging.error('url is required')
            return None

        completeUrl = self.yourApiEndpoint + url

        headers = {
            'Authorization': f"Bearer { accessToken }"
        }

        if method in [ 'PATCH', 'POST'] and body is None:
            logging.error(f"body is required when using { method } { completeUrl }")
        logging.debug(' call info url={}, header= {}, body = {}'.format(completeUrl, headers, body))

        try:
            if method == 'GET':
                response = requests.get(completeUrl, headers=headers)
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

    # Then implement your service specific APIs
    def getAllDevices(self):
        return self._callApi(url='/devices')

    def unsubscribe(self):
        return self._callApi(method='DELETE', url='/subscription')

    def getUserInfo(self):
        return self._callApi(url='/user/info')
    '''

    def updateOauthConfig(self):
        self.addOauthParameter('client_id',self.client_ID )
        self.addOauthParameter('client_secret',self.client_SECRET )
        self.addOauthParameter('scope',self.scope_str )
        #self.addOauthParameter('state','dette er en test' )
        #self.addOauthParameter('redirect_uri','https://my.isy/io/api/cloudlink/redirect' )
        self.addOauthParameter('name','Netatmo Test' )
        self.addOauthParameter('cloudlink', True )
        self.addOauthParameter('addRedirect', True )
        logging.debug('updateOauthConfig = {}'.format(self.oauthConfig))
    '''
### Main node server code

    def getAccessToken(self):
        logging.info('Getting access token')
        token = self.token

        if token is not None:
            expiry = token.get('expiry')

            logging.info(f"Token expiry is { expiry }")
            # If expired or expiring in less than 10 min, refresh
            if expiry is None or datetime.fromisoformat(expiry) - timedelta(seconds=600) < datetime.now():
                logging.info('Refresh tokens expired. Initiating refresh.')
                self._oAuthTokensRefresh()
            else:
                logging.info('Refresh tokens is still valid, no need to refresh')

            return self.token.get('access_token')
        else:
            return None
    
    def _oAuthTokensRefresh(self):
        logging.info('Refreshing oAuth tokens')
        logging.debug(f"Token before: { self.token}")
        if self.token:
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': self.token['refresh_token'],
                'client_id': self.client_ID,
                'client_secret': self.client_SECRET
            }
        else:
            logging.info('Access token is not yet available. Please authenticate.')
            #self.poly.Notices['auth'] = 'Please initiate authentication'
            return(None)
        try:
            response = requests.post(self.token_endpoint, data=data)
            response.raise_for_status()
            self.token = response.json()
            logging.info('Refreshing oAuth tokens successful')
            logging.debug(f"Token refresh result [{ type(self.token) }]: { self.token }")
            #self._saveToken(token)

        except requests.exceptions.HTTPError as error:
            logging.error(f"Failed to refresh oAuth token: { error }")
            # NOTE: If refresh tokens fails, we keep the existing tokens available.