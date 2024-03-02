
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
import secrets
import urllib.parse
#from udi_interface import LOGGER, Custom
#from oauth import OAuth
try:
    from udi_interface import LOGGER, Custom, OAuth
    logging = LOGGER
    Custom = Custom
except ImportError:
    import logging
    logging.basicConfig(level=logging.DEBUG)



# Implements the API calls to your external service
# It inherits the OAuth class
class TeslaCloud(OAuth):
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
        self.api  = 'api/1'
        self.LOCAL_USER_EMAIL = ''
        self.LOCAL_USER_PASSWORD = ''
        self.LOCAL_IP_ADDRESS = ''
        #self.state = secrets.token_hex(16)
        self.region = ''
        self.handleCustomParamsDone = False
        #self.customerDataHandlerDone = False
        self.customNsHandlerDone = False
        self.temp_unit = 'C'

        self.scopeList = ['energy_cmds']
        
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
    #def refresh_token(self):
    #    logging.debug('checking token for refresh')
        

    # Your service may need to access custom params as well...
    
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
                    self.poly.Notices['region'] = 'Unknown Region specified (NA = Nort America + Asia (-China), EU = Europe. middle East, Africa, CN = China)'
                elif 'region' in self.poly.Notices:
                    self.poly.Notices['region'].clear()
        else:
            logging.warning('No region found')
            self.customParameters['region'] = 'enter region (NA, EU, CN)'
            self.region = None
            self.poly.Notices['region'] = 'Region not specified (NA = Nort America + Asia (-China), EU = Europe. middle East, Africa, CN = China)'
            
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
    
    def authendicated(self):
        try:
            #logging.debug('authendicated - {}'.format(self.getOauthSettings()))
            self.getAccessToken()
            return(True)
        except ValueError as err:
            logging.warning('Access token is not yet available. Please authenticate.')
            #self.poly.Notices['auth'] = 'Please initiate authentication'
            return (False)
        
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
            return
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
    ########################################
    ############################################

    def teslaGetProduct(self):
        temp = self._callApi('GET', '/products')
        return(temp)

    def teslaCloudInfo(self):
        if self.site_id == '':
            try:
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
        site = self._callApi('POST', '/energy_sites'+self.site_id +'/time_of_use_settings', json=payload)

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
        site = r.json()
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