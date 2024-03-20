
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
import urllib
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
        self.authendication_done = False
        self.temp_unit = 'C'
        
        self.poly = polyglot

        logging.info('External service connectivity initialized...')

        time.sleep(1)

        self.OPERATING_MODES = [ "self_consumption", "autonomous"]
        self.EXPORT_RULES = ['battery_ok', 'pv_only', 'never']
        self.HISTORY_TYPES = ['backup', 'charge', 'energy' ]
        self.DAY_HISTORY = ['today', 'yesterday']
        #self.TOU_MODES = ["economics", "balanced"]
        self.daysConsumption = {}
        self.tokeninfo = {}
        self.touScheduleList = []
        self.connectionEstablished = False
        self.cloudAccess =  self.connectionEstablished
        self.products = {}
        self.site_id = ''
        self.history_data = {}


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
        while not self.authendication_done :
            try:
                accessToken = self.getAccessToken()
                self.authendication_done = True
            except ValueError as err:
                logging.error(' No access tyoken exist - try again : {}'.format(err))
                time.sleep(1)
                self.authendication_done = False

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
        return(self.authendication_done)
 
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


    # Then implement your service specific APIs
    ########################################
    ############################################
   
    def tesla_get_products(self):
        power_walls= {}
        logging.debug('tesla_get_products ')
        temp = self._callApi('GET','/products' )
        logging.debug('products: {} '.format(temp))
        if 'response' in temp:
            for indx in range(0,len(temp['response'])):
                site = temp['response'][indx]
                if 'energy_site_id' in site:
                    power_walls[site['energy_site_id' ]] = site
        return(power_walls)
    
    def tesla_get_live_status(self, site_id):
        logging.debug('tesla_get_live_status ')
        temp = self._callApi('GET','/energy_sites/'+site_id +'/live_status' )
        logging.debug('live_status: {} '.format(temp))
        if 'response' in temp:
            self.site_live_info = temp['response']

    def tesla_get_site_info(self, site_id):
        logging.debug('tesla_get_site_info ')
        temp = self._callApi('GET','/energy_sites/'+site_id +'/site_info' )
        logging.debug('site_info: {} '.format(temp))   
        if 'response' in temp:
            self.site_info = temp['response']

    def tesla_set_backup_percent(self, site_id, reserve_pct):
        logging.debug('tesla_set_backup_percent : {}'.format(reserve_pct))
        reserve = int(reserve_pct)
        body = {'backup_reserve_percent': reserve}
        temp = self._callApi('POST','/energy_sites/'+site_id +'/backup', body )
        logging.debug('backup_percent: {} '.format(temp))   



    def tesla_set_off_grid_vehicle_charging(self, site_id, reserve_pct ):
        logging.debug('tesla_set_off_grid_vehicle_charging : {}'.format(reserve_pct))
        reserve = int(reserve_pct)
        body = {'off_grid_vehicle_charging_reserve_percent': reserve}
        temp = self._callApi('POST','/energy_sites/'+site_id +'/off_grid_vehicle_charging_reserve', body )
        logging.debug('off_grid_vehicle_charging: {} '.format(temp))   

    def tesla_set_grid_import_export(self, site_id, solar_charge, pref_export):
        logging.debug('tesla_set_grid_import_export : {} {}'.format(solar_charge, pref_export))
        if pref_export in self.EXPORT_RULES:
            body = {'disallow_charge_from_grid_with_solar_installed' : solar_charge,
                    'customer_preferred_export_rule': pref_export}
            temp = self._callApi('POST','/energy_sites/'+site_id +'/grid_import_export', body )
            logging.debug('operation: {} '.format(temp))               


    def tesla_set_operation(self, site_id, mode):
        logging.debug('tesla_set_operation : {}'.format(mode))
        if mode in self.OPERATING_MODES:
            body = {'default_real_mode' : mode}
            temp = self._callApi('POST','/energy_sites/'+site_id +'/operation', body )
            logging.debug('operation: {} '.format(temp))               


    def tesla_set_storm_mode(self, site_id, mode):
        logging.debug('tesla_set_storm_mode : {}'.format(mode))
        body = {'enabled' : mode}
        temp = self._callApi('POST','/energy_sites/'+site_id +'/storm_mode', body )
        logging.debug('storm_mode: {} '.format(temp))               


    def tesla_get_today_history(self, site_id, type):
        logging.debug('tesla_get_today_history : {}'.format(type))
        if type in self.HISTORY_TYPES:
            t_now = datetime.now(get_localzone())

            t_now_date = t_now.strftime('%Y-%m-%d')
            t_now_time = t_now.strftime('T%H:%M:%S')
            tz_offset = t_now.strftime('%z')   
            tz_offset = tz_offset[0:3]+':'+tz_offset[-2:]
            tz_str = t_now.tzname()
            t_start_str = t_now_date+'T00:00:00'+tz_offset
            t_end_str = t_now_date+t_now_time+tz_offset
            params = {
                    'kind'          : type,
                    'start_date'    : t_start_str,
                    'end_date'      : t_end_str,
                    'period'        : 'day',
                    'time_zone'     : tz_str
                    #'time_zone'     : 'America/Los_Angeles'
                    }
            logging.debug('body = {}'.format(params))
            hist_data = self._callApi('GET','/energy_sites/'+site_id +'/calendar_history?'+'kind='+str(type)+'&start_date='+t_start_str+'&end_date='+t_end_str+'&period=day'+'&time_zone='+tz_str  )
            #temp = self._callApi('GET','/energy_sites/'+site_id +'/calendar_history?'+ urllib.parse.urlencode(params) )
            logging.debug('result ({}) = {}'.format(type, hist_data))
            self.process_history_data(site_id, type, hist_data)


    def tesla_get_yesterday_history(self, site_id, type):
        logging.debug('tesla_get_yesterday_history : {}'.format(type))
        if type in self.HISTORY_TYPES:
            t_now = datetime.now(get_localzone())
            t_yesterday = t_now - timedelta(days = 1)

            t_yesterday_date = t_yesterday.strftime('%Y-%m-%d')
            #t_now_time = t_yesterday.strftime('T%H:%M:%S%z')
            tz_offset = t_now.strftime('%z')   
            tz_offset = tz_offset[0:3]+':'+tz_offset[-2:]
            tz_str = t_now.tzname()
            t_start_str = t_yesterday_date+'T00:00:00'+tz_offset
            t_end_str = t_yesterday_date+'T23:59:59'+tz_offset
            params = {
                    'kind'          : type,
                    'start_date'    : t_start_str,
                    'end_date'      : t_end_str,
                    'period'        : 'day',
                    'time_zone'     : tz_str
                    #'time_zone'     : 'America/Los_Angeles'
                    }
            logging.debug('body = {}'.format(params))
            hist_data = self._callApi('GET','/energy_sites/'+site_id +'/calendar_history?'+'kind='+str(type)+'&start_date='+t_start_str+'&end_date='+t_end_str+'&period=day'+'&time_zone='+tz_str  )
            #temp = self._callApi('GET','/energy_sites/'+site_id +'/calendar_history?'+ urllib.parse.urlencode(params) )
            logging.debug('result ({})= {}'.format(type, hist_data))
            self.process_history_data(site_id, type, hist_data)



    def tesla_get_2day_history(self, site_id, type):
        logging.debug('tesla_get_2day_history : {}'.format(type))
        if type in self.HISTORY_TYPES:
            t_now = datetime.now(get_localzone())
            t_yesterday = t_now - timedelta(days = 1)
            t_yesterday_date = t_yesterday.strftime('%Y-%m-%d')
            t_now_date = t_now.strftime('%Y-%m-%d')
            t_now_time = t_now.strftime('T%H:%M:%S')
            tz_offset = t_now.strftime('%z')   
            tz_offset = tz_offset[0:3]+':'+tz_offset[-2:]
            tz_str = t_now.tzname()
            t_start_str = t_yesterday_date+'T00:00:00'+tz_offset
            t_end_str = t_now_date+t_now_time+tz_offset
            params = {
                    'kind'          : type,
                    'start_date'    : t_start_str,
                    'end_date'      : t_end_str,
                    'period'        : 'day',
                    'time_zone'     : tz_str
                    #'time_zone'     : 'America/Los_Angeles'
                    }
            logging.debug('body = {}'.format(params))
            hist_data = self._callApi('GET','/energy_sites/'+site_id +'/calendar_history?'+'kind='+str(type)+'&start_date='+t_start_str+'&end_date='+t_end_str+'&period=day'+'&time_zone='+tz_str  )
            #temp = self._callApi('GET','/energy_sites/'+site_id +'/calendar_history?'+ urllib.parse.urlencode(params) )
            if 'response' in hist_data:
                logging.debug('result ({}) = {}'.format(type, hist_data['response']))
                self.process_history_data(site_id, type, hist_data['response'])
            else:
                logging.info ('No data obtained')

    def update_dates(self):
        t_now = datetime.now(get_localzone())
        t_yesterday = t_now - timedelta(days = 1)
        self.yesterday_date = t_yesterday.strftime('%Y-%m-%d')
        self.today_date = t_now.strftime('%Y-%m-%d')

    def process_energy_data(self, side_id, hdata):
        logging.debug('process_energy_data: {}'.format(hdata))
    
        for indx in range(0,len(hdata['timeseries'])):
            e_data = hdata['timeseries'][indx]
            time_str = e_data['timestamp']
            dt_object = datetime.fromisoformat(time_str)
            date_str = dt_object.strftime('%Y-%m-%d')
            if date_str == self.today_date:
                date_key = 'today'                
            elif date_str == self.yesterday_date:
                date_key == 'yesterday'
            else:
                date_key == 'unknown'
            if date_key != 'unknown':
                self.history_data[side_id]['energy'][date_key] = e_data

    def process_backup_data(self, side_id, hdata):
        logging.debug('process_backup_data: {}'.format(hdata))
        if hdata['events_count'] > 0:
            for indx in range(0,len(hdata['events'])):
                event = hdata['events'][indx]
        # need to figure put how to deal with dates
            


    def process_charge_data(self, side_id, hdata):
        logging.debug('process_charge_data: {}'.format(hdata))

    def process_history_data(self, site_id, type, hist_data):
        logging.debug('process_history_data - {} {} {}'.format(site_id, type, hist_data))
        self.update_dates()
        if site_id not in self.history_data:
            self.history_data[site_id] = {}
        if type not in self.history_data[site_id]:
            self.history_data[site_id][type] = {}

        if type == 'energy':
            self.process_energy_data(site_id, hist_data)
        elif type == 'backup':
            self.process_backup_data(site_id, hist_data)
        elif type == 'charge':
            self.process_charge_data(site_id, hist_data)
        else:
            logging.error('Unknown type provided: {}'.format(type))

        logging.debug('history data: {}'.format(self.history_data))
        




    '''
    def teslaGet_backup_time_remaining(self):
       
        temp = self._callApi('GET','/energy_sites'+self.site_id +'/backup_time_remaining' )
        self.backup_time_remaining = temp['response']['time_remaining_hours'] 
        return(self.backup_time_remaining )       
        
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
    '''
    def teslaGet_tariff_rate(self):
        tariff_data = self._callApi('GET', '/energy_sites'+self.site_id +'/tariff_rate')
        if tariff_data['response']:
            return(tariff_data['response'])
        else:
            return(None)
     
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

    Query the cloud for the different types of data.  If all
    data access fails (i.e. returns None), then return
    false to indicate that.

    Otherwise, return true to indiate that access is good
    '''
    def teslaUpdateCloudData(self, site_id, mode):
        if mode == 'critical':
            temp =self.tesla_get_live_status(site_id)
            if temp != None:
                self.site_live = temp
                return(True)
            tesla_get_today_history(SITE_ID, 'TODAY')
        elif mode == 'all':
            access = False
            temp =self.tesla_get_live_status(site_id)
            if temp != None:
                self.site_live = temp
                access = True
                
            temp = self.tesla_get_site_info('site_info')
            if temp != None:
                self.site_info = temp
                access = True
            logging.debug('self.site_info {}'.format(self.site_info))    
            
            self.tesla_get_today_history(site_id, 'energy')
            self.tesla_get_yesterday_history(site_id, 'energy')
            self.tesla_get_today_history(site_id, 'backup')
            self.tesla_get_yesterday_history(site_id, 'backup')
            self.tesla_get_today_history(site_id, 'charge')
            self.tesla_get_yesterday_history(site_id, 'charge')
            return(access)


    def supportedOperatingModes(self):
        return( self.OPERATING_MODES )


   

    def isConnectedToPW(self):
        return( self.authendicated())

 
   
    def teslaGetSolar(self):
        return(self.site_info['components']['solar'])

    def teslaExtractStormMode(self):
        return(self.site_live_info['storm_mode_active'])


    def teslaExtractBackupPercent(self):
        return(self.site_info['backup_reserve_percent'])
    
    def tesla_total_battery(self):
        return(self.site_live_info['total_pack_energy'])
        
    def tesla_remaining_battery (self):
        return(self.site_live_info['energy_left'])
    

    
    def tesla_island_staus(self):
        return(self.site_live_info['island_status'])
    
    def tesla_grid_staus(self):
        return(self.site_live_info['grid_status'])
    
    def tesla_grid_service_active(self):
        return(self.site_live_info['grid_services_active'])

    def tesla_grid_power(self):
        return(self.site_live_info['grid_power'])
    
    def tesla_generator_power(self):
        return(self.site_live_info['generator_power'])
    
    def tesla_load_power(self):
        return(self.site_live_info['load_power'])
    
    def tesla_battery_power(self):
        return(self.site_live_info['battery_power'])
    
    def tesla_solar_power(self):
        return(self.site_live_info['solar_power'])

    '''
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


        except  Exception as e:
            logging.error('Exception teslaExtractTouTime ' + str(e))
            logging.error('No schedule idenfied')
            return(-1)


    def teslaSetTimeOfUseMode (self, touMode):
        self.touMode = touMode
        self.teslaSetTimeOfUse()

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
    '''

    '''
    		*'solar_energy_exported': 22458, 
			'generator_energy_exported': 0, 
			*'grid_energy_imported': 23080, 
			'grid_services_energy_imported': 7.25, 
			'grid_services_energy_exported': 11.8125, 
			*'grid_energy_exported_from_solar': 15831, 
			*'grid_energy_exported_from_generator': 0, 
			*'grid_energy_exported_from_battery': 77, 
			
			'battery_energy_exported': 10638, 
			'battery_energy_imported_from_grid': 15837,
			'battery_energy_imported_from_solar': 71, 
			'battery_energy_imported_from_generator': 0, 
			energy flow
			'consumer_energy_imported_from_grid': 7243, 
			'consumer_energy_imported_from_solar': 6556, 
			'consumer_energy_imported_from_battery': 10561, 
			'consumer_energy_imported_from_generator': 0}]}}
    '''
    def tesla_grid_energy_import(self, day):
        if day in self.DAY_HISTORY:
            return(self.history_data[self.site_id]['energy'][day]['grid_energy_imported'])
        
    def tesla_grid_energy_export(self, day):    
        if day in self.DAY_HISTORY:
            return(self.history_data[self.site_id]['energy'][day]['grid_energy_exported_from_solar'] + self.history_data[self.site_id]['energy'][day]['grid_energy_exported_from_generator'] + self.history_data[self.site_id]['energy'][day]['grid_energy_exported_from_battery'])

    def tesla_solar_to_grid_energy(self, day): 
        if day in self.DAY_HISTORY:
            return(self.history_data[self.site_id]['energy'][day]['grid_energy_exported_from_solar'])

    def tesla_solar_energy_exported(self, day):
        if day in self.DAY_HISTORY:
            return(self.history_data[self.site_id]['energy'][day]['solar_energy_exported'])

    def tesla_home_energy_total(self, day):    
        if day in self.DAY_HISTORY:
            return(self.history_data[self.site_id]['energy'][day]['consumer_energy_imported_from_grid'] + self.history_data[self.site_id]['energy'][day]['consumer_energy_imported_from_solar'] + self.history_data[self.site_id]['energy'][day]['consumer_energy_imported_from_battery'] + self.history_data[self.site_id]['energy'][day]['consumer_energy_imported_from_generator'] )


    def  tesla_home_energy_solar(self, day):   
        if day in self.DAY_HISTORY:
            return(self.history_data[self.site_id]['energy'][day]['consumer_energy_imported_from_solar'])
        
    def  tesla_home_energy_battery(self, day):   
        if day in self.DAY_HISTORY:
            return(self.history_data[self.site_id]['energy'][day]['consumer_energy_imported_from_battery'])   
        
    def  tesla_home_energy_grid(self, day):   
        if day in self.DAY_HISTORY:
            return(self.history_data[self.site_id]['energy'][day]['consumer_energy_imported_from_grid'])          

    def  tesla_home_energy_generator(self, day):   
        if day in self.DAY_HISTORY:
            return(self.history_data[self.site_id]['energy'][day]['consumer_energy_imported_from_generator'])            


    def tesla_battery_energy_import(self, day):        
        if day in self.DAY_HISTORY:
            return(self.history_data[self.site_id]['energy'][day]['battery_energy_imported_from_grid'] + self.history_data[self.site_id]['energy'][day]['battery_energy_imported_from_solar'] + self.history_data[self.site_id]['energy'][day]['battery_energy_imported_from_generator']  )

    def tesla_battery_energy_export(self, day):
        if day in self.DAY_HISTORY:
            return(self.history_data[self.site_id]['energy'][day]['battery_energy_exported'])
        


    '''
    def teslaExtractDaysSolar(self):
        return(self.history_data[self.site_id]['energy']['today']['solar_energy_exported'])
        #return(self.daysConsmuption['solar_power'])
    
    def teslaExtractDaysConsumption(self):
        return(self.history_data[self.site_id]['energy']['today']['solar_energy_exported'])
        #return(self.daysConsumption['consumed_power'])

    def teslaExtractDaysGeneration(self):
        return(self.history_data[self.site_id]['energy']['today']['solar_energy_exported'])
        #return(self.daysConsumption['net_generation'])

    def teslaExtractDaysBattery(self): 
        return(self.history_data[self.site_id]['energy']['today']['solar_energy_exported'])
        #return(self.daysConsumption['battery_power'])

    def teslaExtractDaysGrid(self):         
        return(self.history_data[self.site_id]['energy']['today']['solar_energy_exported'])
        #return(self.daysConsumption['net_power'])

    def teslaExtractDaysGridServicesUse(self):
        return(self.history_data[self.site_id]['energy']['today']['solar_energy_exported'])
        #return(self.daysConsumption['grid_services_power'])

    def teslaExtractDaysGeneratorUse(self):
        return(self.history_data[self.site_id]['energy']['today']['solar_energy_exported'])
        #return(self.daysConsumption['generator_power'])  

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

    def teslaExtractConnectedTesla(self):       
        return(True)

    def teslaExtractRunning(self):  
        return(True)
    
    #???
    def teslaExtractPowerSupplyMode(self):  
        return(True)

    def teslaExtractGridServiceActive(self):
        if self.site_live['grid_services_active']: 
            return(1)
        else:
            return(0)
    '''