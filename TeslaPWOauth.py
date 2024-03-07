
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
from datetime import timedelta, datetime
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


#from udi_interface import LOGGER, Custom, OAuth, ISY
#logging = udi_interface.LOGGER
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
        self.customParameters = Custom(self.poly, 'customparams')
        #self.scope_str = None
        self.EndpointNA= 'https://fleet-api.prd.na.vn.cloud.tesla.com'
        self.EndpointEU= 'https://fleet-api.prd.eu.vn.cloud.tesla.com'
        self.EndpointCN= 'https://fleet-api.prd.cn.vn.cloud.tesla.cn'
        self.api  = '/api/1'
        self.LOCAL_USER_EMAIL = ''
        self.LOCAL_USER_PASSWORD = ''
        self.LOCAL_IP_ADDRESS = ''
        self.local_access_enabled = False
        self.cloud_access_enabled = False
        #self.state = secrets.token_hex(16)
        self.region = ''
        self.handleCustomParamsDone = False
        #self.customerDataHandlerDone = False
        self.customNsHandlerDone = False
        self.customOauthHandlerDone = False
        self.temp_unit = 'C'
        
        self.poly = polyglot

        logging.info('External service connectivity initialized...')

        time.sleep(1)

        self.OPERATING_MODES = ["backup", "self_consumption", "autonomous"]
        self.TOU_MODES = ["economics", "balanced"]
        self.daysConsumption = {}
        self.tokeninfo = {}
        self.touScheduleList = []
        self.connectionEstablished = False
        self.cloudAccess =  self.connectionEstablished
        self.products = {}
        self.site_id = ''


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
        while not (self.customParamsDone() and self.customNsDone()):
            logging.debug('Waiting for initilization to complete before oAuth')
            time.sleep(5)
        #logging.debug('oauth Parameters: {}'.format(self.getOauthSettings()))
        super().oauthHandler(token)
        #self.customOauthHandlerDone = True
        logging.debug('oauthHandler Finished')

    def customNsDone(self):
        return(self.customNsHandlerDone)
    
    def customDateDone(self):
        return(self.customDataHandlerDone )

    def customParamsDone(self):
        return(self.handleCustomParamsDone)

    #def customOauthDone(self):
    #    return(self.customOauthHandlerDone )
    # Your service may need to access custom params as well...


    def local_access(self):
        return(self.local_access_enabled)
    
    def cloud_access(self):
        return(self.cloud_access_enabled)
    
    
    
    def main_module_enabled(self, node_name):
        logging.debug('main_module_enabled called {}'.format(node_name))
        if node_name in self.customParameters :           
            return(int(self.customParameters[node_name]) == 1)
        else:
            self.customParameters[node_name] = 1 #add and enable by default
            self.poly.Notices['home_id'] = 'Check config to select which home/modules should be used (1 - used, 0 - not used) - then restart'
            return(True)

                
    def customParamsHandler(self, userParams):
        self.customParameters.load(userParams)
        logging.debug('customParamsHandler called {}'.format(userParams))

        oauthSettingsUpdate = {}
        #oauthSettingsUpdate['parameters'] = {}
        oauthSettingsUpdate['token_parameters'] = {}
        # Example for a boolean field

        if 'region' in userParams:
            if self.customParameters['region'] != 'enter region (NA, EU, CN)':
                self.region = str(self.customParameters['region'])
                if self.region.upper() not in ['NA', 'EU', 'CN']:
                    logging.error('Unsupported region {}'.format(self.region))
                    self.poly.Notices['region'] = 'Unknown Region specified (NA = North America + Asia (-China), EU = Europe. middle East, Africa, CN = China)'
                #else:

        else:
            logging.warning('No region found')
            self.customParameters['region'] = 'enter region (NA, EU, CN)'
            self.region = None
            self.poly.Notices['region'] = 'Region not specified (NA = Nort America + Asia (-China), EU = Europe. middle East, Africa, CN = China)'
   
        if 'local_access_en' in self.customParameters:
            if self.customParameters['local_access_en'] != '':
                self.local_access_enabled = self.customParameters['local_access_en'].upper() == 'TRUE'
        else:
            logging.warning('No local_access_enabled found')
            self.customParameters['local_access_en'] = 'True/False'

        if 'cloud_access_en' in self.customParameters:      
            if self.customParameters['cloud_access_en'] != '':
                self.cloud_access_enabled = self.customParameters['cloud_access_en'].upper() == 'TRUE'
        else:
            logging.warning('No cloud_access_en found')
            self.customParameters['cloud_access_en'] = 'True/False'

        if 'LOCAL_USER_EMAIL' in self.customParameters:
            if self.customParameters['LOCAL_USER_EMAIL'] != '':
                self.LOCAL_USER_EMAIL= str(self.customParameters['LOCAL_USER_EMAIL'])
        else:
            logging.warning('No LOCAL_USER_EMAIL found')
            self.customParameters['LOCAL_EMAIL'] = 'enter LOCAL_EMAIL'
            self.LOCAL_USER_EMAIL = None

        if 'LOCAL_USER_PASSWORD' in self.customParameters:
            if self.customParameters['LOCAL_USER_PASSWORD'] != '':
                self.LOCAL_USER_PASSWORD= str(self.customParameters['LOCAL_USER_PASSWORD'] )
                #oauthSettingsUpdate['client_secret'] = self.customParameters['clientSecret']
                #secret_ok = True
        else:
            logging.warning('No LOCAL_USER_PASSWORD found')
            self.customParameters['LOCAL_USER_PASSWORD'] = 'enter LOCAL_USER_PASSWORD'
            self.LOCAL_USER_PASSWORD = None

        if 'LOCAL_IP_ADDRESS' in self.customParameters:
            if self.customParameters['LOCAL_IP_ADDRESS'] != 'x.x.x.x':
                self.LOCAL_IP_ADDRESS= str(self.customParameters['LOCAL_IP_ADDRESS'] )
                #oauthSettingsUpdate['client_secret'] = self.customParameters['clientSecret']
                #secret_ok = True
        else:
            logging.warning('No LOCAL_IP_ADDRESS found')
            self.customParameters['LOCAL_IP_ADDRESS'] = 'enter LOCAL_IP_ADDRESS'
            self.LOCAL_IP_ADDRESS = None
        logging.debug('region {}'.format(self.region))
        oauthSettingsUpdate['scope'] = self.scope 
        oauthSettingsUpdate['auth_endpoint'] = 'https://auth.tesla.com/oauth2/v3/authorize'
        oauthSettingsUpdate['token_endpoint'] = 'https://auth.tesla.com/oauth2/v3/token'
        #oauthSettingsUpdate['redirect_uri'] = 'https://my.isy.io/api/cloudlink/redirect'
        #oauthSettingsUpdate['cloudlink'] = True
        oauthSettingsUpdate['addRedirect'] = True
        #oauthSettingsUpdate['state'] = self.state
        if self.region.upper() == 'NA':
            self.Endpoint = self.EndpointNA
        elif self.region.upper() == 'EU':
            self.Endpoint = self.EndpointEU
        elif self.region.upper() == 'CN':
            self.Endpoint = self.EndpointCN
        else:
            logging.error('Unknow region specified {}'.format(self.region))
            return
           
        self.yourApiEndpoint = self.Endpoint+self.api 
        oauthSettingsUpdate['token_parameters']['audience'] = self.Endpoint
        #oauthSettingsUpdate['token_parameters']['client_id'] = '6e635ec38dc4-4d2a-a35e-f164b51f3d96'
        #oauthSettingsUpdate['token_parameters']['client_secret'] = 'ta-secret.S@z5uUjp*sxoS2rS'
        #oauthSettingsUpdate['token_parameters']['addRedirect'] = True
        self.updateOauthSettings(oauthSettingsUpdate)
        time.sleep(0.1)
        temp = self.getOauthSettings()
        #logging.debug('Updated oAuth config 2: {}'.format(temp))
        
        self.handleCustomParamsDone = True
        self.poly.Notices.clear()
    

    def add_to_parameters(self,  key, value):
        '''add_to_parameters'''
        self.customParameters[key] = value

    def check_parameters(self, key, value):
        '''check_parameters'''
        if key in self.customParameters:
            return(self.customParameters[key]  == value)
        else:
            return(False)

    def getAccessToken(self):
        # Make sure we have received tokens before attempting to renew

        if self._oauthTokens is not None and self._oauthTokens.get('refresh_token'):
            expiry = self._oauthTokens.get('expiry')

            # If expired or expiring in less than 60 seconds, refresh
            if (expiry is None or datetime.fromisoformat(expiry) - timedelta(seconds=60) < datetime.now()):

                logging.info(f"Access tokens: Token is expired since { expiry }. Initiating refresh.")
                self._oAuthTokensRefresh()
            else:
                logging.info(f"Access tokens: Token is still valid until { expiry }, no need to refresh")

            return self._oauthTokens.get('access_token')
        else:
            raise ValueError('Access token is not available')


    
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

        except requests.exceptions.HTTPError as error:
            logging.error(f"Failed to refresh oAuth token: { error }")
            # NOTE: If refresh tokens fails, we keep the existing tokens available.        
    
    def authendicated(self):
        try:
            
            accessToken = self.getAccessToken()
        except ValueError as err:
            logging.warning('Access token is not yet available. Please authenticate.')
            self.poly.Notices['auth'] = 'Please initiate authentication'
            logging.debug('oauth error: {}'.format(err))
            return(False)
        if accessToken is None:
            logging.error('Access token is not available')
            return(False)
        else:
            return(True)
    '''
    def setOauthScope(self, scope):
        oauthSettingsUpdate = {}
        logging.debug('Set Scope to {}'.format(scope))
        oauthSettingsUpdate['scope'] = str(scope)
        self.updateOauthSettings(oauthSettingsUpdate)
    
    def setOauthName(self, name):
        oauthSettingsUpdate = {} 
        logging.debug('Set name to {}'.format(name))
        oauthSettingsUpdate['name'] = str(name)
        self.updateOauthSettings(oauthSettingsUpdate)
    

    def _insert_refreshToken(self, refresh_token, clientId, clientSecret):
        data = {
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token,
                'client_id': clientId,
                'client_secret':  clientSecret
                }
        try:
            response = requests.post('https://api.netatmo.com/oauth2/token' , data=data)
            response.raise_for_status()
            token = response.json()
            logging.info('Refreshing tokens successful')
            logging.debug(f"Token refresh result [{ type(token) }]: { token }")
            self._saveToken(token)
            return('Success')
          
        except requests.exceptions.HTTPError as error:
            logging.error(f"Failed to refresh  token: { error }")
            return(None)
            # NOTE: If refresh tokens fails, we keep the existing tokens available.
    '''

    # Call your external service API
    def _callApi(self, method='GET', url=None, body=None):
        # When calling an API, get the access token (it will be refreshed if necessary)
        try:
            accessToken = self.getAccessToken()
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
    ########################################
    ############################################

    def teslaGetProduct(self):
        temp = self._callApi('GET', '/products')
        return(temp)

    def teslaCloudInfo(self):
        if self.site_id == '':
            try:
                while not self.authendicated():
                    logging.info('Waiting for authntication to complete - teslaCloudInfo')
                    time.sleep(2)
                products = self.teslaGetProduct()
                nbrProducts = products['count']
                for index in range(0,nbrProducts): #Can only handle one power wall setup - will use last one found
                    if 'resource_type' in products['response'][index]:
                        if products['response'][index]['resource_type'] == 'battery':
                            self.site_id ='/'+ str(products['response'][index]['energy_site_id'] )
                            self.products = products['response'][index]
                return(True)
            except Exception as e:
                logging.error('Exception teslaCloudInfo: ' + str(e))
                return(False)
        else:
            return(True)


    def teslaSetOperationMode(self, mode):
        logging.debug('teslaSetOperationMode : {}'.format(mode))
        try:
          
            if mode  in self.OPERATING_MODES:
                payload = {'default_real_mode': mode}
                site = self._callApi('POST', '/energy_sites'+self.site_id +'/operation', payload)
                logging.debug('site {}'.format(site))
                if site['response']['code'] <210:
                    self.site_info['default_real_mode'] = mode
                    return (True)
                else:
                    return(False)
            else:
                return(False)
     
        except Exception as e:
            logging.error('Exception teslaSetOperationMode: ' + str(e))
            logging.error('Error setting operation mode')
            return(False)    
            
    def teslaGet_backup_time_remaining(self):
       
        temp = self._callApi('GET','/energy_sites'+self.site_id +'/backup_time_remaining' )
        self.backup_time_remaining = temp['response']['time_remaining_hours'] 
        return(self.backup_time_remaining )       
        '''
        S = self.teslaApi.teslaConnect()
        with requests.Session() as s:
            try:
                s.auth = OAuth2BearerToken(S['access_token'])   
                r = s.get(self.TESLA_URL + self.API+ '/energy_sites'+self.site_id +'/backup_time_remaining', headers=self.Header)          
                temp = r.json()
                self.backup_time_remaining = temp['response']['time_remaining_hours'] 
                return(self.backup_time_remaining )
            except Exception as e:
                logging.error('Exception teslaGetSiteInfo: ' + str(e))
                logging.error('Trying to reconnect')
                self.teslaApi.tesla_refresh_token( )
                return(None)                
        '''
        
    def teslaGet_tariff_rate(self):
        tariff_data = self._callApi('GET', '/energy_sites'+self.site_id +'/tariff_rate')
        if tariff_data['response']:
            return(tariff_data['response'])
        else:
            return(None)
            '''
            S = self.teslaApi.teslaConnect()
            with requests.Session() as s:
                try:
                    s.auth = OAuth2BearerToken(S['access_token'])   
                    r = s.get(self.TESLA_URL + self.API+ '/energy_sites'+self.site_id +'/tariff_rate', headers=self.Header)          
                    tariff_data = r.json()
                    return(tariff_data['response'])
                except Exception as e:
                    logging.error('Exception teslaGetSiteInfo: ' + str(e))
                    logging.error('Trying to reconnect')
                    self.teslaApi.tesla_refresh_token( )
                    return(None)    
            '''

    def teslaGetSiteInfo(self, mode):
        #if self.connectionEstablished:
        #S = self.__teslaConnect()
        if mode == 'site_status':
            site = self._callApi('GET', '/energy_sites'+self.site_id +'/site_status' )          

        elif mode == 'site_live':
            site = self._callApi('GET', '/energy_sites'+self.site_id +'/live_status' )          

        elif mode == 'site_info':
            site = self._callApi('GET', '/energy_sites'+self.site_id +'/site_info' )          
        
        elif mode == 'site_history_day':
            site = self._callApi('GET', '/energy_sites'+self.site_id +'/history',{'kind':'power', 'period':'day'}) 

        elif mode == 'rate_tariffs':
            site = self._callApi('GET', '/energy_sites'+self.site_id +'/rate_tariffs' )          

        elif mode == 'tariff_rate':
            site = self._callApi('GET', '/energy_sites'+self.site_id +'/tariff_rate' )          

        elif mode == 'backup_time_remaining':
            site = self._callApi('GET', '/energy_sites'+self.site_id +'/backup_time_remaining')          
                                                                                                                            
        else:
            #logging.debug('Unknown mode: '+mode)
            return(None)
        return(site['response'])

        '''
        S = self.teslaApi.teslaConnect()
        with requests.Session() as s:
            try:
                s.auth = OAuth2BearerToken(S['access_token'])            
                if mode == 'site_status':
                    r = s.get(self.TESLA_URL + self.API+ '/energy_sites'+self.site_id +'/site_status', headers=self.Header)          
                    site = r.json()
                elif mode == 'site_live':
                    r = s.get(self.TESLA_URL + self.API+ '/energy_sites'+self.site_id +'/live_status', headers=self.Header)          
                    site = r.json()
                elif mode == 'site_info':
                    r = s.get(self.TESLA_URL + self.API+ '/energy_sites'+self.site_id +'/site_info', headers=self.Header)          
                    site = r.json()            
                elif mode == 'site_history_day':
                    r = s.get(self.TESLA_URL + self.API+ '/energy_sites'+self.site_id +'/history', headers=self.Header, json={'kind':'power', 'period':'day'}) 
                    site = r.json() 
                elif mode == 'rate_tariffs':
                    r = s.get(self.TESLA_URL + self.API+ '/energy_sites'+self.site_id +'/rate_tariffs', headers=self.Header)          
                    site = r.json()
                elif mode == 'tariff_rate':
                    r = s.get(self.TESLA_URL + self.API+ '/energy_sites'+self.site_id +'/tariff_rate', headers=self.Header)          
                    site = r.json()
                elif mode == 'backup_time_remaining':
                    r = s.get(self.TESLA_URL + self.API+ '/energy_sites'+self.site_id +'/backup_time_remaining', headers=self.Header)          
                    site = r.json()
                                                                                                                                  
                else:
                    #logging.debug('Unknown mode: '+mode)
                    return(None)
                return(site['response'])
            except Exception as e:
                logging.error('Exception teslaGetSiteInfo: ' + str(e))
                logging.error('Error getting data' + str(mode))
                logging.error('Trying to reconnect')
                self.teslaApi.tesla_refresh_token( )
                return(None)
        '''

    def teslaSetBackoffLevel(self, backupPercent):
        #if self.connectionEstablished:
        logging.debug('teslaSetBackoffLevel {}'.format(backupPercent))
        if backupPercent >=0 and backupPercent <=100:
            payload = {'backup_reserve_percent': backupPercent}
            site = self._callApi('POST', '/energy_sites'+self.site_id +'/backup', payload)        
            if site['response']['code'] <210:
                self.site_info['backup_reserve_percent'] = backupPercent
                return (True)
            else:
                return(False) 
        else: return(False)      
        '''
        S = self.teslaApi.teslaConnect()
        #S = self.__teslaConnect()
        with requests.Session() as s:
            try:
                s.auth = OAuth2BearerToken(S['access_token'])
                if backupPercent >=0 and backupPercent <=100:
                    payload = {'backup_reserve_percent': backupPercent}
                    r = s.post(self.TESLA_URL +  self.API + '/energy_sites'+self.site_id +'/backup', headers= self.Header,  json=payload)        
                    site = r.json()
                    if site['response']['code'] <210:
                        self.site_info['backup_reserve_percent'] = backupPercent
                        return (True)
                    else:
                        return(False)

                else:
                    return(False)
                    #site="Backup Percent out of range 0-100:" + str(backupPercent)
                    #logging.debug(site)   
            except  Exception as e:
                logging.error('Exception teslaSetBackoffLEvel: ' + str(e))
                logging.error('Error setting bacup percent')
                self.teslaApi.tesla_refresh_token( ) 
                return(False)
        '''


    def teslaSetTimeOfUse (self):
        #if self.connectionEstablished:
        temp = {}
        temp['tou_settings'] = {}
        temp['tou_settings']['optimization_strategy'] = self.touMode
        temp['tou_settings']['schedule'] = self.touScheduleList
        payload = temp
        site = self._callApi('POST', '/energy_sites'+self.site_id +'/time_of_use_settings', payload)

        if site['response']['code'] <210:
            self.site_info['tou_settings']['optimization_strategy'] = self.touMode
            self.site_info['tou_settings']['schedule']= self.touScheduleList
            return (True)
        else:
            return(False)
        '''
        S = self.teslaApi.teslaConnect() 
        #S = self.__teslaConnect()
        with requests.Session() as s:
            try:
                s.auth = OAuth2BearerToken(S['access_token'])

                payload = temp
                r = s.post(self.TESLA_URL +  self.API+ '/energy_sites'+self.site_id +'/time_of_use_settings', headers=self.Header, json=payload)
                site = r.json()
                if site['response']['code'] <210:
                    self.site_info['tou_settings']['optimization_strategy'] = self.touMode
                    self.site_info['tou_settings']['schedule']= self.touScheduleList
                    return (True)
                else:
                    return(False)
            except Exception as e:
                logging.error('Exception teslaSetTimeOfUse: ' + str(e))
                logging.error('Error setting time of use parameters')
                self.teslaApi.tesla_refresh_token( ) 
                return(False)
        '''



    def teslaSetStormMode(self, EnableBool):

        #if self.connectionEstablished:

        payload = {'enabled': EnableBool}
        site = self._callApi('POST',  '/energy_sites'+self.site_id +'/storm_mode', payload)
        if site['response']['code'] <210:
            self.site_info['user_settings']['storm_mode_enabled'] = EnableBool
            return (True)
        else:
            return(False)
        '''
        S = self.teslaApi.teslaConnect()
        #S = self.__teslaConnect()
        with requests.Session() as s:
            try:
                s.auth = OAuth2BearerToken(S['access_token'])
                payload = {'enabled': EnableBool}
                r = s.post(self.TESLA_URL +  self.API+ '/energy_sites'+self.site_id +'/storm_mode', headers = self.Header, json=payload)
                site = r.json()
                if site['response']['code'] <210:
                    self.site_info['user_settings']['storm_mode_enabled'] = EnableBool
                    return (True)
                else:
                    return(False)
            except Exception as e:
                logging.error('Exception teslaSetStormMode: ' + str(e))
                logging.error('Error setting storm mode')
                self.teslaApi.tesla_refresh_token( )
                return(False)
        '''

    def teslaCloudConnect(self ):
        logging.debug('teslaCloudConnect')
        #self.tokeninfo = self.teslaAuth.tesla_refresh_token( )
        return(self.tokeninfo)

    def teslaRetrieveCloudData(self):
        if self.teslaCloudInfo(): 
            self.connectionEstablished = True
            self.site_status = self.teslaGetSiteInfo('site_status')

            self.cloudAccess = self.teslaUpdateCloudData('all')
            #self.touSchedule = self.teslaExtractTouScheduleList()
            #logging.debug('touSchedule: {}'.format(self.touSchedule))
        else:
            logging.error('Error getting cloud data')
            return(None)
        logging.debug('site info : {}'.format(self.site_info))
        if 'tou_settings' in self.site_info:
            if 'optimization_strategy' in self.site_info['tou_settings']:
                self.touMode = self.site_info['tou_settings']['optimization_strategy']
            else:
                self.touMode = None
            if 'schedule' in self.site_info['tou_settings']:
                self.touScheduleList =self.site_info['tou_settings']['schedule']
            else:
                self.touScheduleList = []
        else:
            self.touMode = None
            self.touScheduleList = []
            logging.debug('Tou mode not set')
        logging.debug('self.touScheduleList : {}'.format(self.touScheduleList ) )

    '''
    Query the cloud for the different types of data.  If all
    data access fails (i.e. returns None), then return
    false to indicate that.

    Otherwise, return true to indiate that access is good
    '''
    def teslaUpdateCloudData(self, mode):
        if mode == 'critical':
            temp =self.teslaGetSiteInfo('site_live')
            if temp != None:
                self.site_live = temp
                return(True)
        elif mode == 'all':
            access = False
            temp= self.teslaGetSiteInfo('site_live')
            if temp != None:
                self.site_live = temp
                access = True
                
            temp = self.teslaGetSiteInfo('site_info')
            if temp != None:
                self.site_info = temp
                access = True
            logging.debug('self.site_info {}'.format(self.site_info))    
            
            temp = self.teslaGetSiteInfo('site_history_day')            
            if temp != None:
                self.site_history = temp
                access = True
            self.teslaCalculateDaysTotals()
            return(access)
        else:
            access = False
            temp= self.teslaGetSiteInfo('site_live')
            if temp != None:
                self.site_live = temp
                access = True
                
            temp = self.teslaGetSiteInfo('site_info')            
            if temp != None:
                self.site_info = temp
                access = True
            logging.debug('self.site_info {}'.format(self.site_info))    
            temp = self.teslaGetSiteInfo('site_history_day')            
            if temp != None:
                self.site_history = temp
                access = True


            temp = self.teslaGetSiteInfo('site_status')
            if temp != None:
                self.site_status = temp
                access = True
            self.teslaCalculateDaysTotals()
            return(access)

    def supportedOperatingModes(self):
        return( self.OPERATING_MODES )

    def supportedTouModes(self):
        return(self.TOU_MODES)

   

    def isConnectedToPW(self):
        return( self.authendicated())

    #def getRtoken(self):
    #    return(self.teslaApi.getRtoken())


    def TeslaGet_current_rate_state(self):
        logging.debug('get_current_state')
        try:
            now = datetime.now()
            tarif_data = self.teslaGet_tariff_rate()
            seasonFound = False
            for season in tarif_data['seasons']:
      
                monthFrom = tarif_data['seasons'][season]['fromMonth']
                monthTo = tarif_data['seasons'][season]['toMonth']
                dayFrom = tarif_data['seasons'][season]['fromDay'] 
                dayTo = tarif_data['seasons'][season]['toDay'] 
                #logging.debug('season {} - months {} {} days {}{}'.format(season, monthFrom, monthTo, dayFrom, dayTo ))
                if  (monthFrom <= monthTo and (int(now.month)  >= monthFrom and now.month <= monthTo)) or ( monthFrom > monthTo and (now.month  >= monthFrom or now.month <= monthTo)): 
                        if now.month == monthFrom:
                            seasonFound =  now.day >= dayFrom
                        elif now.month == monthTo:
                            seasonFound =   now.day <= dayTo
                        else:
                            seasonFound =  True                                                               
                if seasonFound:
                    seasonNow = season     
                    break
            periodFound = False
            for period in tarif_data['seasons'][seasonNow]['tou_periods']:   
                #logging.debug('period {}  season {}'.format(period,seasonNow))

                for timeRange in tarif_data['seasons'][seasonNow]['tou_periods'][period]:
                    wdayFrom = timeRange['fromDayOfWeek']
                    wdayTo =timeRange['toDayOfWeek']
                    hourFrom = timeRange['fromHour']
                    hourTo = timeRange['toHour']
                    minFrom = timeRange['fromMinute']
                    minTo = timeRange['toMinute']    
             
                    if wdayFrom <= wdayTo and ( wdayFrom <= now.weekday() and wdayTo >= now.weekday()) or (wdayTo <= wdayFrom and ( wdayFrom >= now.weekday() or wdayTo <= now.weekday())):
                        if (hourFrom <= hourTo and (now.hour >= hourFrom and now.hour <= hourTo)) or (hourFrom > hourTo and (now.hour >= hourFrom or now.hour <= hourTo)):
                            if now.hour == hourFrom:
                                periodFound = now.min > minFrom
                            elif now.hour == hourTo:
                                periodFound = now.min < minTo
                            else:
                                periodFound = True
                    if periodFound:
                        periodNow = period
                        break

            if seasonNow in tarif_data['energy_charges']:
                buyRateNow = tarif_data['energy_charges'][seasonNow][periodNow]
            else:
                buyRateNow = tarif_data['energy_charges']['ALL']

            return seasonNow, periodNow, buyRateNow
        except Exception as E:
            logging.error('TeslaGet_current_state Exception: {}'.format(E))
            return None, None, 0

    def peak_info(self):
        logging.debug('peak_info')

    def get_current_buy_price(self):
        logging.debug('get_current_buy_price')

    def get_current_sell_price(self):
        logging.debug('get_current_sell_price')


   
    def teslaGetSolar(self):
        return(self.products['components']['solar'])

  
    def teslaExtractStormMode(self):
        if self.site_info['user_settings']['storm_mode_enabled']:
            return(1)
        else:
            return(0)

    def teslaExtractBackupPercent(self):
        return(self.site_info['backup_reserve_percent'])

    def teslaUpdateTouScheduleList(self, peakMode, weekdayWeekend, startEnd, time_s):
        indexFound = False
        try:
            if weekdayWeekend == 'weekend':
                days = set([6,0])
            else:
                days = set([1,2,3,4,5])

            #if self.touScheduleList == None:
            self.touScheduleList = self.teslaExtractTouScheduleList()

            for index in range(0,len(self.touScheduleList)):
                if self.touScheduleList[index]['target']== peakMode and set(self.touScheduleList[index]['week_days']) == days:
                    indexFound = True
                    if startEnd == 'start':
                        self.touScheduleList[index]['start_seconds'] = time_s
                    else:
                        self.touScheduleList[index]['end_seconds'] = time_s
            if not(indexFound):
                temp = {}
                temp['target']= peakMode
                temp['week_days'] = days
                if startEnd == 'start':
                    temp['start_seconds'] = time_s
                else:
                    temp['end_seconds'] = time_s
                self.touScheduleList.append(temp)
                indexFound = True
            return(indexFound)
        except  Exception as e:
                logging.error('Exception teslaUpdateTouScheduleLite: ' + str(e))
                logging.error('Error updating schedule')
                #self.teslaApi.tesla_refresh_token( ) 
                return(False)

    def teslaSetTouSchedule(self, peakMode, weekdayWeekend, startEnd, time_s):
        if self.teslaUpdateTouScheduleList( peakMode, weekdayWeekend, startEnd, time_s):
            self.teslaSetTimeOfUse()

    def  teslaExtractTouTime(self, days, peakMode, startEnd ):
        indexFound = False
        logging.debug('teslaExtractTouTime - self.touScheduleList {}'.format(self.touScheduleList ))
        try:
            if days == 'weekend':
                days =set([6,0])
            else:
                days = set([1,2,3,4,5])
            value = -1
            for data in self.touScheduleList:
                logging.debug('Looping data {}'.format(data))
                if data['week_days'][0] == 1 and data['week_days'][1] == 0: # all daya
                    if startEnd == 'start':
                        value = data['start_seconds']                    
                    else:
                        value = data['end_seconds']
                elif set(days) == set(data['week_days']):
                    if startEnd == 'start':
                        value = data['start_seconds']
                    else:
                        value = data['end_seconds']
            return(value)
            '''
            for index in range(0,len(self.touScheduleList)):
                if self.touScheduleList[index]['target'] == peakMode and (set(self.touScheduleList[index]['week_days']) == days or set(self.touScheduleList[index]['week_days']) ==[1,0]):
                    if startEnd == 'start':
                        value = self.touScheduleList[index]['start_seconds']
                    else:
                        value = self.touScheduleList[index]['end_seconds']
                    indexFound = True
                    logging.debug('Value {}'.format(value))
                    return(value)
            if not(indexFound):       
                self.site_info = self.teslaGetSiteInfo('site_info')
                self.touScheduleList = self.teslaExtractTouScheduleList()
                for index in range(0,len(self.touScheduleList)):
                    if self.touScheduleList[index]['target']== peakMode and (set(self.touScheduleList[index]['week_days']) == days or set(self.touScheduleList[index]['week_days']) ==[1,0]):
                        if startEnd == 'start':
                            value = self.touScheduleList[index]['start_seconds']
                        else:
                            value = self.touScheduleList[index]['end_seconds']
                        indexFound = True
                        return(value)
            if not(indexFound): 
                logging.debug('No schedule appears to be set')            
                return(-1)
            '''

        except  Exception as e:
            logging.error('Exception teslaExtractTouTime ' + str(e))
            logging.error('No schedule idenfied')
            return(-1)


    def teslaSetTimeOfUseMode (self, touMode):
        self.touMode = touMode
        self.teslaSetTimeOfUse()

    '''
    def teslaSetTimeOfUse (self):
        #if self.connectionEstablished:
        temp = {}
        S = self.teslaApi.teslaConnect() 
        #S = self.__teslaConnect()
        with requests.Session() as s:
            try:
                s.auth = OAuth2BearerToken(S['access_token'])
                temp['tou_settings'] = {}
                temp['tou_settings']['optimization_strategy'] = self.touMode
                temp['tou_settings']['schedule'] = self.touScheduleList
                payload = temp
                r = s.post(self.TESLA_URL +  self.API+ '/energy_sites'+self.site_id +'/time_of_use_settings', headers=self.Header, json=payload)
                site = r.json()
                if site['response']['code'] <210:
                    self.site_info['tou_settings']['optimization_strategy'] = self.touMode
                    self.site_info['tou_settings']['schedule']= self.touScheduleList
                    return (True)
                else:
                    return(False)
            except Exception as e:
                logging.error('Exception teslaSetTimeOfUse: ' + str(e))
                logging.error('Error setting time of use parameters')
                self.teslaApi.tesla_refresh_token( ) 
                return(False)
    '''

    def teslaExtractTouMode(self):
        return(self.site_info['tou_settings']['optimization_strategy'])

    def teslaExtractTouScheduleList(self):
        
        self.touScheduleList = self.site_info['tou_settings']['schedule']
        return( self.touScheduleList )

    def teslaExtractChargeLevel(self):
        return(round(self.site_live['percentage_charged'],2))
        
    def teslaExtractBackoffLevel(self):
        return(round(self.site_info['backup_reserve_percent'],1))

    def teslaExtractGridStatus(self): 
        return(self.site_live['island_status'])


    def teslaExtractSolarSupply(self):
        return(self.site_live['solar_power'])

    def teslaExtractBatterySupply(self):     
        return(self.site_live['battery_power'])

    def teslaExtractGridSupply(self):     
        return(self.site_live['grid_power'])

    def teslaExtractLoad(self): 
        return(self.site_live['load_power'])

    def teslaExtractGeneratorSupply (self):
        return(self.site_live['generator_power'])

    def teslaCalculateDaysTotals(self):
        try:
            data = self.site_history['time_series']
            nbrRecords = len(data)
            index = nbrRecords-1
            dateStr = data[index]['timestamp']
            Obj = datetime.strptime(dateStr, "%Y-%m-%dT%H:%M:%S%z")

            solarPwr = 0
            batteryPwr = 0
            gridPwr = 0
            gridServicesPwr = 0
            generatorPwr = 0
            loadPwr = 0

            prevObj = Obj
            while ((prevObj.day == Obj.day) and  (prevObj.month == Obj.month) and (prevObj.year == Obj.year) and (index >= 1)):

                lastDuration =  prevObj - Obj
                timeFactor= lastDuration.total_seconds()/60/60
                solarPwr = solarPwr + data[index]['solar_power']*timeFactor
                batteryPwr = batteryPwr + data[index]['battery_power']*timeFactor
                gridPwr = gridPwr + data[index]['grid_power']*timeFactor
                gridServicesPwr = gridServicesPwr + data[index]['grid_services_power']*timeFactor
                generatorPwr = generatorPwr + data[index]['generator_power']*timeFactor

                index = index - 1
                prevObj = Obj
                dateStr = data[index]['timestamp']
                Obj = datetime.strptime(dateStr, "%Y-%m-%dT%H:%M:%S%z")
            loadPwr = gridPwr + solarPwr + batteryPwr + generatorPwr + gridServicesPwr
            genPwr = solarPwr + batteryPwr + generatorPwr + gridServicesPwr

            ySolarPwr = data[index]['solar_power']*timeFactor
            yBatteryPwr = data[index]['battery_power']*timeFactor
            yGridPwr = data[index]['grid_power']*timeFactor
            yGridServicesPwr = data[index]['grid_services_power']*timeFactor
            YGeneratorPwr = data[index]['generator_power']*timeFactor

            prevObj = Obj
            while ((prevObj.day == Obj.day) and  (prevObj.month == Obj.month) and (prevObj.year == Obj.year) and (index >= 1)):
                lastDuration =  prevObj - Obj
                timeFactor= lastDuration.total_seconds()/60/60
                ySolarPwr = ySolarPwr + data[index]['solar_power']*timeFactor
                yBatteryPwr = yBatteryPwr + data[index]['battery_power']*timeFactor
                yGridPwr = yGridPwr + data[index]['grid_power']*timeFactor
                yGridServicesPwr = yGridServicesPwr + data[index]['grid_services_power']*timeFactor
                YGeneratorPwr = YGeneratorPwr + data[index]['generator_power']*timeFactor

                index = index - 1
                prevObj = Obj
                dateStr = data[index]['timestamp']
                Obj = datetime.strptime(dateStr, "%Y-%m-%dT%H:%M:%S%z")

            yLoadPwr = yGridPwr + ySolarPwr + yBatteryPwr + YGeneratorPwr + yGridServicesPwr
            ygenPwr = ySolarPwr + yBatteryPwr + YGeneratorPwr + yGridServicesPwr

            self.daysConsumption = {'solar_power': solarPwr, 'consumed_power': loadPwr, 'net_power':gridPwr
                                ,'battery_power': batteryPwr ,'grid_services_power': gridServicesPwr, 'generator_power' : generatorPwr
                                ,'yesterday_solar_power': ySolarPwr, 'yesterday_consumed_power': yLoadPwr, 'yesterday_net_power':yGridPwr
                                ,'yesterday_battery_power': yBatteryPwr ,'yesterday_grid_services_power': yGridServicesPwr, 'yesterday_generator_power' : YGeneratorPwr, 
                                'net_generation': genPwr, 'net_generation': ygenPwr}
        
            #print(self.daysConsumption)
            return(True)
        except Exception as e:
            logging.error('Exception teslaCalculateDaysTotal: ' + str(e))
            logging.error(' Error obtaining time data')
  

    def teslaExtractDaysSolar(self):
        return(self.daysConsumption['solar_power'])
    
    def teslaExtractDaysConsumption(self):     
        return(self.daysConsumption['consumed_power'])

    def teslaExtractDaysGeneration(self):         
        return(self.daysConsumption['net_generation'])

    def teslaExtractDaysBattery(self):         
        return(self.daysConsumption['battery_power'])

    def teslaExtractDaysGrid(self):         
        return(self.daysConsumption['net_power'])

    def teslaExtractDaysGridServicesUse(self):         
        return(self.daysConsumption['grid_services_power'])

    def teslaExtractDaysGeneratorUse(self):         
        return(self.daysConsumption['generator_power'])  

    def teslaExtractYesteraySolar(self):
        return(self.daysConsumption['yesterday_solar_power'])
    
    def teslaExtractYesterdayConsumption(self):     
        return(self.daysConsumption['yesterday_consumed_power'])

    def teslaExtractYesterdayGeneraton(self):         
        return(self.daysConsumption['net_generation'])

    def teslaExtractYesterdayBattery(self):         
        return(self.daysConsumption['yesterday_battery_power'])

    def teslaExtractYesterdayGrid(self):         
        return(self.daysConsumption['yesterday_net_power'])

    def teslaExtractYesterdayGridServiceUse(self):         
        return(self.daysConsumption['yesterday_grid_services_power'])

    def teslaExtractYesterdayGeneratorUse(self):         
        return(self.daysConsumption['yesterday_generator_power'])  

    def teslaExtractOperationMode(self):         
        return(self.site_info['default_real_mode'])


    '''
    def teslaExtractConnectedTesla(self):       
        return(True)

    def teslaExtractRunning(self):  
        return(True)
    '''
    #???
    def teslaExtractPowerSupplyMode(self):  
        return(True)

    def teslaExtractGridServiceActive(self):
        if self.site_live['grid_services_active']: 
            return(1)
        else:
            return(0)
