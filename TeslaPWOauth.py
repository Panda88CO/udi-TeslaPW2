
#!/usr/bin/env python3

### Your external service class
'''
Your external service class can be named anything you want, and the recommended location would be the lib folder.
It would look like this:

External service sample code
Copyright (C) 2023 Universal Devices

MIT License
'''


import numbers
from datetime import timedelta, datetime
from TeslaOauth import teslaAccess
from tzlocal import get_localzone

try:
    import udi_interface
    logging = udi_interface.LOGGER
    Custom = udi_interface.Custom
except ImportError:
    import logging
    logging.basicConfig(level=30)


#from udi_interface import logging, Custom, OAuth, ISY
#logging = udi_interface.logging
#Custom = udi_interface.Custom
#ISY = udi_interface.ISY



# Implements the API calls to your external service
# It inherits the OAuth class
class teslaPWAccess(teslaAccess):
    yourApiEndpoint = 'https://fleet-api.prd.na.vn.cloud.tesla.com'

    def __init__(self, polyglot, scope):
        super().__init__(polyglot, scope)
        logging.info('teslaPWAccess initializing')
        self.poly = polyglot
        self.scope = scope
        logging.info('External service connectivity initialized...')
        self.OPERATING_MODES = [ "self_consumption", "autonomous"]
        self.EXPORT_RULES = ['battery_ok', 'pv_only', 'never']
        self.HISTORY_TYPES = ['backup', 'charge', 'energy' ]
        self.DAY_HISTORY = ['today', 'yesterday']
        self.TOU_MODES = ["economics", "balanced"]
        self.daysConsumption = {}
        self.tokeninfo = {}
        self.touScheduleList = []
        self.connectionEstablished = False
        self.cloudAccess =  self.connectionEstablished
        self.products = {}
        self.history_data = {}
        self.previous_date_str = '' # no previous data stored
        self.date_changed = True
        self.t_now_date = ''
        self.t_now_time = ''
        self.tz_offset = ''
        self.tz_str = ''
        self.t_yesterday_date = ''
        self.NaN = -2147483647
        self.total_pack_energy = {}
        self.installation_tz = {}
        #self.update_date_time()
        self.site_info = {}
        self.site_live_info = {}
        #time.sleep(1)
        self.PWiniitalized = True
        self.wall_connector = 0
        #while not self.handleCustomParamsDone:
        #    logging.debug('Waiting for customParams to complete - getAccessToken')
        #    time.sleep(0.2)
        # self.getAccessToken()

    # Then implement your service specific APIs
    ########################################
    ############################################
   
    def tesla_get_products(self) -> dict:
        power_walls= {}
        logging.debug('tesla_get_products ')
        try:
            temp = self._callApi('GET','/products' )
            logging.debug('products: {} '.format(temp))
            if 'response' in temp:
                for indx in range(0,len(temp['response'])):
                    site = temp['response'][indx]
                    if 'energy_site_id' in site:
                        power_walls[str(site['energy_site_id' ])] = site
                        if 'total_pack_energy' in site:
                            self.total_pack_energy[str(site['energy_site_id' ])] = site['total_pack_energy' ] 
                        if 'wall_connectors' in site['components']:
                            self.wall_connector = len(site['components']['wall_connectors'])
                
            return(power_walls)
        except Exception as e:
            logging.error('tesla_get_products Exception : {}'.format(e))


    def tesla_get_live_status(self, site_id) -> None:
        logging.debug('tesla_get_live_status ')
        try:
            if site_id not in self.total_pack_energy:
                self.total_pack_energy[site_id] = self.NaN
            if site_id is not None:
                temp = self._callApi('GET','/energy_sites/'+site_id +'/live_status' )
                logging.debug('live_status: {} '.format(temp))
                if 'response' in temp:
                    self.site_live_info[site_id] = temp['response']
                    if 'total_pack_energy' in self.site_live_info[site_id]:
                        self.total_pack_energy[site_id] = self.site_live_info[site_id]['total_pack_energy']
            
                    return(self.site_live_info[site_id])
            else:
                return (None)
        except Exception as e:
            logging.error('tesla_get_live_status Exception : {}'.format(e))
            return(None)
                          
    def tesla_get_site_info(self, site_id) -> None:
        logging.debug(f'tesla_get_site_info {site_id}')
        try:
            if site_id not in self.installation_tz:
                self.installation_tz[site_id] = None
            temp = self._callApi('GET','/energy_sites/'+site_id +'/site_info' )
            logging.debug('site_info: {} '.format(temp))           
            if 'response' in temp:
                self.site_info[site_id] = temp['response']
                logging.debug('tesla_get_site_info'.format(self.site_info[site_id] ))
                if 'components' in self.site_info[site_id]:
                    if 'installation_time_zone' in self.site_info[site_id]:
                        self.installation_tz[site_id] = str(self.site_info[site_id]['installation_time_zone'])
                logging.debug('Timezone {}'.format(self.installation_tz))
                return(self.site_info)
        except Exception as e:
            logging.error('tesla_get_site_info Exception : {}'.format(e))

    def tesla_set_backup_percent(self, site_id, reserve_pct) -> None:
        logging.debug('tesla_set_backup_percent : {}'.format(reserve_pct))
        try:
            reserve = int(reserve_pct)
            body = {'backup_reserve_percent': reserve}
            temp = self._callApi('POST','/energy_sites/'+site_id +'/backup', body )
            logging.debug('backup_percent: {} '.format(temp))   
        except Exception as e:
            logging.error('tesla_set_backup_percent Exception : {}'.format(e))

    def tesla_set_off_grid_vehicle_charging(self, site_id, reserve_pct ) -> None:
        logging.debug('tesla_set_off_grid_vehicle_charging : {}'.format(reserve_pct))
        try:

            reserve = int(reserve_pct)
            body = {'off_grid_vehicle_charging_reserve_percent': reserve}
            temp = self._callApi('POST','/energy_sites/'+site_id +'/off_grid_vehicle_charging_reserve', body )
            logging.debug('off_grid_vehicle_charging: {} '.format(temp))   
        except Exception as e:
            logging.error('tesla_set_off_grid_vehicle_charging Exception : {}'.format(e))
        

    def tesla_set_grid_import_export(self, site_id, solar_charge, pref_export):
        logging.debug('tesla_set_grid_import_export : {} {}'.format(solar_charge, pref_export))
        try:
            if pref_export in self.EXPORT_RULES:
                body = {'disallow_charge_from_grid_with_solar_installed' : solar_charge,
                        'customer_preferred_export_rule': pref_export}
                temp = self._callApi('POST','/energy_sites/'+site_id +'/grid_import_export', body )
                logging.debug('operation: {} '.format(temp))               
        except Exception as e:
            logging.error('tesla_set_grid_import_export Exception : {}'.format(e))
        

    def tesla_set_operation(self, site_id, mode) -> None:
        logging.debug('tesla_set_operation : {}'.format(mode))
        try:
            if mode in self.OPERATING_MODES:
                body = {'default_real_mode' : mode}
                temp = self._callApi('POST','/energy_sites/'+site_id +'/operation', body )
                logging.debug('operation: {} '.format(temp))               
        except Exception as e:
            logging.error('tesla_set_operation Exception : {}'.format(e))

    def tesla_set_storm_mode(self, site_id, mode) -> None:
        logging.debug('tesla_set_storm_mode : {}'.format(mode))
        try:
            body = {'enabled' : mode}
            temp = self._callApi('POST','/energy_sites/'+site_id +'/storm_mode', body )
            logging.debug('storm_mode: {} '.format(temp))               
        except Exception as e:
            logging.error('tesla_set_storm_mode Exception : {}'.format(e))

    def update_date_time(self, site_id) -> None:
        t_now = datetime.now(get_localzone())
        today_date_str = t_now.strftime('%Y-%m-%d')
        self.date_changed = (today_date_str != self.previous_date_str)
        self.previous_date_str = today_date_str
        self.t_now_date = today_date_str
        self.t_now_time = t_now.strftime('T%H:%M:%S')
        tz_offset = t_now.strftime('%z')   
        self.tz_offset = tz_offset[0:3]+':'+tz_offset[-2:]
        #self.tz_str = t_now.tzname()
        t_yesterday = t_now - timedelta(days = 1)
        self.t_yesterday_date = t_yesterday.strftime('%Y-%m-%d')
        logging.debug('timezone info : {}'.format(self.installation_tz))
        if self.installation_tz[site_id]:
            self.tz_str = self.installation_tz[site_id]
        else:
            self.tz_str = t_now.tzname()

        #t_now = datetime.now(get_localzone())
        #t_yesterday = t_now - timedelta(days = 1)
        #self.yesterday_date = t_yesterday.strftime('%Y-%m-%d')
        #self.today_date = self.t_now.strftime('%Y-%m-%d')


    def tesla_get_today_history(self, site_id, type) -> None:
        logging.debug('tesla_get_today_history : {}'.format(type))
        try:
            self.update_date_time(site_id)
            if type in self.HISTORY_TYPES:
                #t_now = datetime.now(get_localzone())
                #self.t_now_date = t_now.strftime('%Y-%m-%d')
                #self.t_now_time = t_now.strftime('T%H:%M:%S')
                #tz_offset = t_now.strftime('%z')   
                #self.tz_offset = tz_offset[0:3]+':'+tz_offset[-2:]

                t_start_str = self.t_now_date+'T00:00:00'+self.tz_offset
                t_end_str = self.t_now_date+self.t_now_time+self.tz_offset
                params = {
                        'kind'          : type,
                        'start_date'    : t_start_str,
                        'end_date'      : t_end_str,
                        'period'        : 'day',
                        'time_zone'     : self.tz_str
                        #'time_zone'     : 'America/Los_Angeles'
                        }
                logging.debug('body = {}'.format(params))
                hist_data = self._callApi('GET','/energy_sites/'+site_id +'/calendar_history?'+'kind='+str(type)+'&start_date='+t_start_str+'&end_date='+t_end_str+'&period=day'+'&time_zone='+self.tz_str  )
                #temp = self._callApi('GET','/energy_sites/'+site_id +'/calendar_history?'+ urllib.parse.urlencode(params) )
                logging.debug('result ({}) = {}'.format(type, hist_data))
                if hist_data:
                    if 'response' in hist_data:
                        self.process_history_data(site_id, type, hist_data['response'])
                    else:
                        logging.info ('No data obtained')
        except Exception as e:
            logging.error('tesla_get_today_history Exception : {}'.format(e))


    def tesla_get_yesterday_history(self, site_id, type) -> None:
        logging.debug('tesla_get_yesterday_history : {}'.format(type))
        try:
            self.update_date_time(site_id)
            if type in self.HISTORY_TYPES:
                #self.prepare_date_time()
                #t_now = datetime.now(get_localzone())
                #t_yesterday = t_now - timedelta(days = 1)
                #t_yesterday_date = t_yesterday.strftime('%Y-%m-%d')
                #t_now_time = t_yesterday.strftime('T%H:%M:%S%z')
                #tz_offset = t_now.strftime('%z')   
                #tz_offset = tz_offset[0:3]+':'+tz_offset[-2:]
                #tz_str = t_now.tzname()
                t_start_str = self.t_yesterday_date+'T00:00:00'+self.tz_offset
                t_end_str = self.t_yesterday_date+'T23:59:59'+self.tz_offset
                params = {
                        'kind'          : type,
                        'start_date'    : t_start_str,
                        'end_date'      : t_end_str,
                        'period'        : 'day',
                        'time_zone'     : self.tz_str
                        #'time_zone'     : 'America/Los_Angeles'
                        }
                logging.debug('body = {}'.format(params))
                hist_data = self._callApi('GET','/energy_sites/'+site_id +'/calendar_history?'+'kind='+str(type)+'&start_date='+t_start_str+'&end_date='+t_end_str+'&period=day'+'&time_zone='+self.tz_str  )
                #temp = self._callApi('GET','/energy_sites/'+site_id +'/calendar_history?'+ urllib.parse.urlencode(params) )
                logging.debug('result ({})= {}'.format(type, hist_data))
                if hist_data:
                    if 'response' in hist_data:
                        self.process_history_data(site_id, type, hist_data['response'])
                    else:
                        logging.info ('No data obtained')
        except Exception as e:
            logging.error('tesla_get_yesterday_history Exception : {}'.format(e))

    def tesla_get_2day_history(self, site_id, type) -> None:
        logging.debug('tesla_get_2day_history : {}'.format(type))
        try:
            self.update_date_time(site_id)
            if type in self.HISTORY_TYPES:
                #t_now = datetime.now(get_localzone())
                #t_yesterday = t_now - timedelta(days = 1)
                #t_yesterday_date = t_yesterday.strftime('%Y-%m-%d')
                #t_now_date = t_now.strftime('%Y-%m-%d')
                #t_now_time = t_now.strftime('T%H:%M:%S')
                #tz_offset = t_now.strftime('%z')   
                #tz_offset = tz_offset[0:3]+':'+tz_offset[-2:]
                #tz_str = t_now.tzname()
                t_start_str = self.t_yesterday_date+'T00:00:00'+self.tz_offset
                t_end_str = self.t_now_date+self.t_now_time+self.tz_offset
                params = {
                        'kind'          : type,
                        'start_date'    : t_start_str,
                        'end_date'      : t_end_str,
                        'period'        : 'day',
                        'time_zone'     : self.tz_str
                        #'time_zone'     : 'America/Los_Angeles'
                        }
                logging.debug('body = {}'.format(params))
                hist_data = self._callApi('GET','/energy_sites/'+site_id +'/calendar_history?'+'kind='+str(type)+'&start_date='+t_start_str+'&end_date='+t_end_str+'&period=day'+'&time_zone='+self.tz_str  )
                #temp = self._callApi('GET','/energy_sites/'+site_id +'/calendar_history?'+ urllib.parse.urlencode(params) )
                if hist_data:
                    if 'response' in hist_data:
                        logging.debug('result ({}) = {}'.format(type, hist_data['response']))
                        self.process_history_data(site_id, type, hist_data['response'])
                    else:
                        logging.info ('No data obtained')
        except Exception as e:
            logging.error('tesla_get_2day_history Exception : {}'.format(e))


    def process_energy_data(self, site_id, hist_data) -> None:
        logging.debug('process_energy_data: {}'.format(hist_data))

        if 'today'  not in self.history_data[site_id]['energy']:
            self.history_data[site_id]['energy']['today'] = {}
        if 'yesterday'  not in self.history_data[site_id]['energy']:
            self.history_data[site_id]['energy']['yesterday'] = {}
        if 'time_series' in hist_data:
            for indx in range(0,len(hist_data['time_series'])):
                # remove old data 
                energy_data = hist_data['time_series'][indx]
                time_str = energy_data['timestamp']
                dt_object = datetime.fromisoformat(time_str)
                date_str = dt_object.strftime('%Y-%m-%d')
                if date_str == self.t_now_date:
                    self.history_data[site_id]['energy']['today'] = {}
                if date_str == self.t_yesterday_date:
                    self.history_data[site_id]['energy']['yesterday'] = {}           

            for indx in range(0,len(hist_data['time_series'])):        
                energy_data = hist_data['time_series'][indx]

                if date_str == self.t_now_date:
                    #date_key = 'today'
                    for key in energy_data:
                        #logging.debug('today energy {} {} {}'.format(key,energy_data[key], type(energy_data[key]) ))
                        if isinstance(energy_data[key], numbers.Number): # only process numbers 
                            if key not in self.history_data[site_id]['energy']['today']:
                                self.history_data[site_id]['energy']['today'][key] = energy_data[key]
                                
                            else:
                                self.history_data[site_id]['energy']['today'][key] += energy_data[key]

                elif date_str == self.t_yesterday_date:
                    #date_key = 'yesterday'
                    for key in energy_data:
                        #logging.debug('yesterday energy {} {} {}'.format(key,energy_data[key], type(energy_data[key]) ))
                        if isinstance(energy_data[key], numbers.Number): # do not process time stamps              
                            if key not in self.history_data[site_id]['energy']['yesterday']:
                                self.history_data[site_id]['energy']['yesterday'][key] = energy_data[key]
                            else:
                                self.history_data[site_id]['energy']['yesterday'][key] += energy_data[key]
        try:
            logging.debug('process_energy_data today {}'.format(self.history_data[site_id]['energy']['today']))
            logging.debug('process_energy_data yesterday {}'.format(self.history_data[site_id]['energy']['yesterday']))
        except Exception as e:
            logging.debug('Parsing energy data exception : {}'.format(e))
    def process_backup_data(self, site_id, hist_data) -> None:
        logging.debug('process_backup_data: {}'.format(hist_data))
        backup_data = hist_data
        total_duration = 0
        date_key = 'unknown' 
        if int(backup_data['events_count']) > 0:
            time_str = backup_data['events'][0]['timestamp'] # all days should be the same
            dt_object = datetime.fromisoformat(time_str)
            date_str = dt_object.strftime('%Y-%m-%d')
            if date_str == self.t_now_date:
                date_key = 'today'                
            elif date_str == self.t_yesterday_date:
                date_key = 'yesterday'
            else:
                date_key = 'unknown'
            for indx in range(0,len(backup_data['events'])):
                event = backup_data['events'][indx]
                total_duration = total_duration + event['duration']
        temp = {}
        temp['total_duration'] = total_duration
        temp['total_events'] = int(backup_data['total_events'])
        if date_key != 'unknown':
            self.history_data[site_id]['backup'][date_key] = temp

        # need to figure put how to deal with dates
            


    def process_charge_data(self, site_id, hist_data) -> None:
        logging.debug('process_charge_data: {}'.format(hist_data))
        charge_data = hist_data
        total_duration = 0
        total_events = 0
        total_energy = 0
        date_key = 'unknown' 
        if 'charge_history' in charge_data:
            if len(charge_data['charge_history']) >  0:
                epoch_time = charge_data['charge_history'][0]['charge_start_time']['seconds'] # all days should be the same
                dt_object = datetime.fromtimestamp(epoch_time)
                date_str = dt_object.strftime('%Y-%m-%d')
                if date_str == self.t_now_date:
                    date_key = 'today'                
                elif date_str == self.t_yesterday_date:
                    date_key = 'yesterday'
                else:
                    date_key = 'unknown'
                total_events = len(charge_data['charge_history'])
                for indx in range(0,len(charge_data['charge_history'])):                    
                    #event = charge_data['charge_history'][indx]
                    total_duration = total_duration + charge_data['charge_history'][indx]['charge_duration']['seconds']
                    total_energy = total_energy + charge_data['charge_history'][indx]['energy_added_wh']
        temp = {}
        temp['total_duration'] = total_duration
        temp['total_events'] = total_events
        temp['total_energy'] = total_energy
        if date_key != 'unknown':
            self.history_data[site_id]['charge'][date_key] = temp




    def process_history_data(self, site_id, type, pw_data) -> None:
        logging.debug('process_history_data - {} {} {}'.format(site_id, type, pw_data))
        self.update_date_time(site_id)
        if site_id not in self.history_data:
            self.history_data[site_id] = {}
        if type not in self.history_data[site_id]:
            self.history_data[site_id][type] = {}

        if type == 'energy':
            self.process_energy_data(site_id, pw_data)
        elif type == 'backup':
            self.process_backup_data(site_id, pw_data)
        elif type == 'charge':
            self.process_charge_data(site_id, pw_data)
        else:
            logging.error('Unknown type provided: {}'.format(type))

        logging.debug('history data: {}'.format(self.history_data))
        



    def teslaUpdateCloudData(self, site_id, mode) -> None:
        logging.debug('teslaUpdateCloudData - {} {}'.format( site_id, mode))
        access = False
        self.update_date_time(site_id)
        #while not self.authenticated():
        #    self.try_authendication()
        #    logging.info('Cloud Access not Authenticated yet - press Autenticate button')
        #    time.sleep(5)
        
        if mode == 'critical':
            temp =self.tesla_get_live_status(site_id)
            self.tesla_get_today_history(site_id, 'energy')
            if temp != None:
                self.site_live_info[site_id] = temp
                access = True
            else:
                access = False
        elif mode == 'all':
            access = False
            temp =self.tesla_get_live_status(site_id)
            if temp != None:
                self.site_live_info[site_id]  = temp
                access = True
            logging.debug('sitelive : {}'.format(self.site_live_info))
            temp = self.tesla_get_site_info(site_id)
            if temp != None:
                self.site_info = temp
                access = True
            logging.debug('site info: {}'.format(self.site_info ))        
            logging.debug('self.site_info {}'.format(self.site_info))    
            
            self.tesla_get_today_history(site_id, 'energy')
            self.tesla_get_today_history(site_id, 'backup')
            #self.tesla_get_today_history(site_id, 'charge')
            if self.date_changed:
                self.tesla_get_yesterday_history(site_id, 'energy')
                self.tesla_get_yesterday_history(site_id, 'backup')
                #self.tesla_get_yesterday_history(site_id, 'charge')
            try:
                tmp = self.history_data[site_id]['energy']['yesteday']['consumer_energy_imported_from_battery']
                if not isinstance(tmp, numbers.Number):
                    yesterday_data_needed = True
                else:
                    yesterday_data_needed = False
            except Exception:
                yesterday_data_needed = True

            if yesterday_data_needed:
                self.tesla_get_yesterday_history(site_id, 'energy')
                self.tesla_get_yesterday_history(site_id, 'backup')
                #self.tesla_get_yesterday_history(site_id, 'charge')
                
            logging.debug('history_data : {}'.format(self.history_data))
        return(access)


    def supportedOperatingModes(self) -> list:
        try:
            return( self.OPERATING_MODES )
        except KeyError:
            return(None)

    def isConnectedToPW(self) -> bool:
        try:
            return( self.authenticated())
        except KeyError:
            return(None)

   
    def teslaSolarInstalled(self, site_id) -> bool:

        try:
            return(self.site_info[site_id]['components']['solar'])
        except KeyError:
            return(None)
        
    def tesla_get_pw_name(self, site_id) -> str:
        try:
            return(self.site_info[site_id]['site_name'])
        except KeyError:
            return(None)
        
    def teslaExtractOperationMode(self, site_id):
        try:
            return(self.site_info[site_id]['default_real_mode'])
        except KeyError:
            return(None)
        
    def teslaExtractStormMode(self, site_id):
        try:
            return(self.site_live_info[site_id]['storm_mode_active'])
        except KeyError:
            return(None)
        
    def teslaExtractBackupPercent(self, site_id):
        logging.debug('teslaExtractBackupPercent : {} {}'.format(site_id, self.site_info))
        try:
            return(self.site_info[site_id]['backup_reserve_percent'])
        except KeyError:
            return(None)
        
    def tesla_total_battery(self, site_id):
        try:
            return(self.site_live_info[site_id][site_id]['total_pack_energy'])
        except KeyError:
            return(None)


    def tesla_remaining_battery (self, site_id):
        try:
            return(self.site_live_info[site_id]['energy_left'])
        except KeyError:
            return(None)
        

    def tesla_island_staus(self, site_id):
        try:
            return(self.site_live_info[site_id]['island_status'])
        except KeyError:
            return(None)    
        
    def tesla_grid_staus(self, site_id):
        try:
            return(self.site_live_info[site_id]['grid_status'])
        except KeyError:
            return(None)    
        
    def tesla_live_grid_service_active(self, site_id):
        try:
            return(self.site_live_info[site_id]['grid_services_active'])
        except KeyError:
            return(None)
        
    def tesla_live_grid_power(self, site_id):
        try:
            return(self.site_live_info[site_id]['grid_power'])
        except KeyError:
            return(None)
            
    def tesla_live_generator_power(self, site_id):
        try:
            return(self.site_live_info[site_id]['generator_power'])
        except KeyError:
            return(None)
            
    def tesla_live_load_power(self, site_id):
        try:
            return(self.site_live_info[site_id]['load_power'])
        except KeyError:
            return(None)


    def tesla_live_battery_power(self, site_id):
        try:
            return(self.site_live_info[site_id]['battery_power'])
        except KeyError:
            return(None)
            
    def tesla_live_solar_power(self, site_id):
        logging.debug('Solar power : {} {}'.format(self.site_live_info[site_id]['solar_power'], self.site_live_info[site_id]))
        try:
            return(self.site_live_info[site_id]['solar_power'])
        except KeyError:
            return(None)
        
    def teslaExtractTouMode(self, site_id):
        try:
            return(self.site_info[site_id]['tou_settings']['optimization_strategy'])
        except KeyError:
            return(None)
        

    def teslaExtractTouScheduleList(self, site_id):  
        try:      
            self.touScheduleList = self.site_live_info[site_id]['components']['tou_settings']['schedule']
            return( self.touScheduleList )
        except KeyError:
            return([])

    def teslaExtractChargeLevel(self, site_id):
        try:
            return(round(self.site_live_info[site_id]['percentage_charged'],2))
        except KeyError:
            return(None)
        
    #def teslaExtractBackoffLevel(self, site_id):
    #    return(round(self.site_info[site_id]['backup_reserve_percent'],1))

    def teslaExtractGridStatus(self, site_id):

        try:
            return(self.site_live_info[site_id]['island_status'])
        except KeyError:
            return(None)
            
    def teslaExtractLoad(self, site_id): 
        try:
            return(self.site_live_info[site_id]['load_power'])
        except KeyError:
            return(None)
        

    def teslaExtractSolarSupply(self, site_id):
        try:
            return(self.site_live_info[site_id]['solar_power'])
        except KeyError:
            return(None)
        

    def teslaExtractBatterySupply(self, site_id):     
        try:
            return(self.site_live_info[site_id]['battery_power'])
        except KeyError:
            return(None)
        

    def teslaExtractGridSupply(self, site_id):     
        try:
            return(self.site_live_info[site_id]['grid_power'])
        except KeyError:
            return(None)
        

    def teslaExtractEnergyRemaining(self, site_id): 
            
        if 'total_pack_energy' in self.site_live_info[site_id]:
            self.total_pack_energy = self.site_live_info[site_id]['total_pack_energy']
        try:
            return(self.site_live_info[site_id]['energy_left'])
        except  KeyError:
            return(None)

    def teslaExtractGeneratorSupply (self, site_id):
        try:
            return(self.site_live_info[site_id]['generator_power'])
        except KeyError:
            return(None)
        
    def teslaExtractGridServiceActive(self, site_id):
        try:
            if self.site_live_info[site_id]['grid_services_enabled']:
                return(1)
            else:
                return(0)
        except KeyError:
            return(99)



    def tesla_grid_energy_import(self, site_id, day):
        try:
            return(self.history_data[site_id]['energy'][day]['grid_energy_imported'])
        except KeyError:
            return(None)
                
    def tesla_grid_energy_export(self, site_id, day):    
        try:
            return(self.history_data[site_id]['energy'][day]['grid_energy_exported_from_solar'] + self.history_data[site_id]['energy'][day]['grid_energy_exported_from_generator'] + self.history_data[site_id]['energy'][day]['grid_energy_exported_from_battery'])
        except KeyError:
            return(None)
        
    def tesla_solar_to_grid_energy(self, site_id, day): 
        try:
            return(self.history_data[site_id]['energy'][day]['grid_energy_exported_from_solar'])
        except KeyError:
            return(None)
        
    def tesla_solar_energy_exported(self, site_id, day):
        try:
            return(self.history_data[site_id]['energy'][day]['solar_energy_exported'])
        except KeyError:
            return(None)
        
    def tesla_home_energy_total(self, site_id, day):    
        try:
            return(self.history_data[site_id]['energy'][day]['consumer_energy_imported_from_grid'] + self.history_data[site_id]['energy'][day]['consumer_energy_imported_from_solar'] + self.history_data[site_id]['energy'][day]['consumer_energy_imported_from_battery'] + self.history_data[site_id]['energy'][day]['consumer_energy_imported_from_generator'] )
        except KeyError:
            return(None)

    def  tesla_home_energy_solar(self, site_id, day):   
        try:
            return(self.history_data[site_id]['energy'][day]['consumer_energy_imported_from_solar'])
        except KeyError:
            return(None)
                
    def  tesla_home_energy_battery(self, site_id, day):   
        try:
            return(self.history_data[site_id]['energy'][day]['consumer_energy_imported_from_battery'])   
        except KeyError:
            return(None)
                
    def  tesla_home_energy_grid(self, site_id, day):   
        try:
            return(self.history_data[site_id]['energy'][day]['consumer_energy_imported_from_grid'])          
        except KeyError:
            return(None)
        
    def  tesla_home_energy_generator(self, site_id, day):   
        try:
            return(self.history_data[site_id]['energy'][day]['consumer_energy_imported_from_generator'])            
        except KeyError:
            return(None)

    def tesla_battery_energy_import(self, site_id, day):        
        try:
            return(self.history_data[site_id]['energy'][day]['battery_energy_imported_from_grid'] + self.history_data[site_id]['energy'][day]['battery_energy_imported_from_solar'] + self.history_data[site_id]['energy'][day]['battery_energy_imported_from_generator']  )
        except KeyError:
            return(None)
        
    def tesla_battery_energy_export(self, site_id, day):
        try:
            return(self.history_data[site_id]['energy'][day]['battery_energy_exported'])
        except KeyError:
            return(None)
                
    def tesla_grid_service_export(self, site_id, day):
        try:
            return(self.history_data[site_id]['energy'][day]['grid_services_energy_exported'])   
        except KeyError:
            return(None)
        
    def tesla_grid_service_import(self, site_id, day):
        try:
            return(self.history_data[site_id]['energy'][day]['grid_services_energy_imported'])
        except KeyError:
            return(None)        

    def tesla_backup_events(self, site_id, day):
        try:
            return(self.history_data[site_id]['backup'][day]['total_events'])
        except KeyError:
            return(None)
                
    def tesla_backup_time(self, site_id, day):
        try:
            return(self.history_data[site_id]['backup'][day]['total_duration'])
        except KeyError:
            return(None)
        
    def tesla_evcharge_power(self, site_id, day):
        try:
            return(self.history_data[site_id]['charge'][day]['total_energy'])
        except KeyError:
            return(None)

    def tesla_evcharge_time(self, site_id, day):
        try:
            return(self.history_data[site_id]['charge'][day]['total_duration'])
        except KeyError:
            return(None)


    '''
    def teslaExtractDaysSolar(self, site_id):
        return(self.history_data[site_id]['energy']['today']['solar_energy_exported'])
        #return(self.daysConsmuption['solar_power'])
    
    def teslaExtractDaysConsumption(self, site_id):
        return(self.history_data[site_id]['energy']['today']['solar_energy_exported'])
        #return(self.daysConsumption['consumed_power'])

    def teslaExtractDaysGeneration(self, site_id):
        return(self.history_data[site_id]['energy']['today']['solar_energy_exported'])
        #return(self.daysConsumption['net_generation'])

    def teslaExtractDaysBattery(self, site_id): 
        return(self.history_data[site_id]['energy']['today']['solar_energy_exported'])
        #return(self.daysConsumption['battery_power'])

    def teslaExtractDaysGrid(self, site_id):         
        return(self.history_data[site_id]['energy']['today']['solar_energy_exported'])
        #return(self.daysConsumption['net_power'])

    def teslaExtractDaysGridServicesUse(self, site_id):
        return(self.history_data[site_id]['energy']['today']['solar_energy_exported'])
        #return(self.daysConsumption['grid_services_power'])

    def teslaExtractDaysGeneratorUse(self, site_id):
        return(self.history_data[site_id]['energy']['today']['solar_energy_exported'])
        #return(self.daysConsumption['generator_power'])  

    def teslaExtractYesteraySolar(self, site_id):
        return(self.daysConsumption['yesterday_solar_power'])
    
    def teslaExtractYesterdayConsumption(self, site_id):     
        return(self.daysConsumption['yesterday_consumed_power'])

    def teslaExtractYesterdayGeneraton(self, site_id):         
        return(self.daysConsumption['net_generation'])

    def teslaExtractYesterdayBattery(self, site_id):         
        return(self.daysConsumption['yesterday_battery_power'])

    def teslaExtractYesterdayGrid(self, site_id):         
        return(self.daysConsumption['yesterday_net_power'])

    def teslaExtractYesterdayGridServiceUse(self, site_id):         
        return(self.daysConsumption['yesterday_grid_services_power'])

    def teslaExtractYesterdayGeneratorUse(self, site_id):         
        return(self.daysConsumption['yesterday_generator_power'])  

    def teslaExtractOperationMode(self, site_id):         
        return(self.site_info['default_real_mode'])

    def teslaExtractConnectedTesla(self, site_id):       
        return(True)

    def teslaExtractRunning(self, site_id):  
        return(True)
    
    #???
    def teslaExtractPowerSupplyMode(self, site_id):  
        return(True)

    def teslaExtractGridServiceActive(self, site_id):
        if self.site_live_info[site_id]['grid_services_active']: 
            return(1)
        else:
            return(0)
    '''