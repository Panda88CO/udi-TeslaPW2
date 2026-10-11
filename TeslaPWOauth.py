
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
            # Map integer if provided (0: pv_only, 1: battery_ok, 2: never)
            export_map = {0: 'pv_only', 1: 'battery_ok', 2: 'never'}
            if isinstance(pref_export, int) or (isinstance(pref_export, str) and pref_export.isdigit()):
                pref_export = export_map.get(int(pref_export), pref_export)

            if pref_export in self.EXPORT_RULES:
                body = {'disallow_charge_from_grid_with_solar_installed' : bool(solar_charge),
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
        if self.installation_tz.get(site_id):
            self.tz_str = self.installation_tz[site_id]
        else:
            self.tz_str = t_now.tzname() or 'UTC'

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
                if type == 'charge':
                    hist_data = self._callApi('GET', f'/energy_sites/{site_id}/telemetry_history?kind=charge&start_date={t_start_str}&end_date={t_end_str}&time_zone={self.tz_str}')
                    if not hist_data or 'response' not in hist_data:
                        hist_data = self._callApi('GET', f'/energy_sites/{site_id}/calendar_history?kind=charge&start_date={t_start_str}&end_date={t_end_str}&period=day&time_zone={self.tz_str}')
                else:
                    hist_data = self._callApi('GET', f'/energy_sites/{site_id}/calendar_history?kind={str(type)}&start_date={t_start_str}&end_date={t_end_str}&period=day&time_zone={self.tz_str}')
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
                if type == 'charge':
                    hist_data = self._callApi('GET', f'/energy_sites/{site_id}/telemetry_history?kind=charge&start_date={t_start_str}&end_date={t_end_str}&time_zone={self.tz_str}')
                    if not hist_data or 'response' not in hist_data:
                        hist_data = self._callApi('GET', f'/energy_sites/{site_id}/calendar_history?kind=charge&start_date={t_start_str}&end_date={t_end_str}&period=day&time_zone={self.tz_str}')
                else:
                    hist_data = self._callApi('GET', f'/energy_sites/{site_id}/calendar_history?kind={str(type)}&start_date={t_start_str}&end_date={t_end_str}&period=day&time_zone={self.tz_str}')
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
        backup_data = hist_data if isinstance(hist_data, dict) else {}
        total_duration = 0
        total_events = int(backup_data.get('total_events', 0))
        date_key = 'unknown' 
        events = backup_data.get('events', [])
        if int(backup_data.get('events_count', 0)) > 0 and len(events) > 0:
            time_str = events[0].get('timestamp')
            if time_str:
                try:
                    dt_object = datetime.fromisoformat(time_str)
                    date_str = dt_object.strftime('%Y-%m-%d')
                    if date_str == self.t_now_date:
                        date_key = 'today'                
                    elif date_str == self.t_yesterday_date:
                        date_key = 'yesterday'
                except Exception:
                    pass
            for event in events:
                total_duration += event.get('duration', 0)
        temp = {
            'total_duration': total_duration,
            'total_events': total_events
        }
        if date_key != 'unknown':
            if 'backup' not in self.history_data[site_id]:
                self.history_data[site_id]['backup'] = {}
            self.history_data[site_id]['backup'][date_key] = temp


    def process_charge_data(self, site_id, hist_data) -> None:
        logging.debug('process_charge_data: {}'.format(hist_data))
        charge_data = hist_data if isinstance(hist_data, dict) else {}
        total_duration = 0
        total_events = 0
        total_energy = 0
        date_key = 'unknown' 

        history_list = charge_data.get('charge_history') or charge_data.get('time_series') or []
        if isinstance(history_list, list) and len(history_list) > 0:
            first_event = history_list[0]
            start_time = first_event.get('charge_start_time') or first_event.get('timestamp')
            dt_object = None
            if isinstance(start_time, dict) and 'seconds' in start_time:
                try:
                    dt_object = datetime.fromtimestamp(start_time['seconds'])
                except Exception:
                    pass
            elif isinstance(start_time, (int, float)):
                try:
                    dt_object = datetime.fromtimestamp(start_time)
                except Exception:
                    pass
            elif isinstance(start_time, str):
                try:
                    dt_object = datetime.fromisoformat(start_time)
                except Exception:
                    pass

            if dt_object:
                date_str = dt_object.strftime('%Y-%m-%d')
                if date_str == self.t_now_date:
                    date_key = 'today'
                elif date_str == self.t_yesterday_date:
                    date_key = 'yesterday'

            total_events = len(history_list)
            for event in history_list:
                dur = event.get('charge_duration', 0)
                if isinstance(dur, dict) and 'seconds' in dur:
                    total_duration += dur['seconds']
                elif isinstance(dur, (int, float)):
                    total_duration += dur

                energy = event.get('energy_added_wh') or event.get('energy_added') or event.get('charging_energy_imported', 0)
                if isinstance(energy, (int, float)):
                    total_energy += energy

        temp = {
            'total_duration': total_duration,
            'total_events': total_events,
            'total_energy': total_energy
        }
        if date_key != 'unknown':
            if 'charge' not in self.history_data[site_id]:
                self.history_data[site_id]['charge'] = {}
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
            temp = self.tesla_get_live_status(site_id)
            if temp is not None:
                self.site_live_info[site_id] = temp
                access = True
            else:
                access = False
        elif mode == 'all':
            access = False
            temp = self.tesla_get_live_status(site_id)
            if temp is not None:
                self.site_live_info[site_id] = temp
                access = True
            logging.debug('sitelive : {}'.format(self.site_live_info))
            temp = self.tesla_get_site_info(site_id)
            if temp is not None:
                self.site_info = temp
                access = True
            logging.debug('site info: {}'.format(self.site_info ))        
            logging.debug('self.site_info {}'.format(self.site_info))    
            
            self.tesla_get_today_history(site_id, 'energy')
            self.tesla_get_today_history(site_id, 'backup')
            self.tesla_get_today_history(site_id, 'charge')
            if self.date_changed:
                self.tesla_get_yesterday_history(site_id, 'energy')
                self.tesla_get_yesterday_history(site_id, 'backup')
                self.tesla_get_yesterday_history(site_id, 'charge')
            else:
                try:
                    tmp = self.history_data.get(site_id, {}).get('energy', {}).get('yesterday', {}).get('consumer_energy_imported_from_battery')
                    yesterday_data_needed = not isinstance(tmp, numbers.Number)
                except Exception:
                    yesterday_data_needed = True

                if yesterday_data_needed:
                    self.tesla_get_yesterday_history(site_id, 'energy')
                    self.tesla_get_yesterday_history(site_id, 'backup')
                    self.tesla_get_yesterday_history(site_id, 'charge')
                
            logging.debug('history_data : {}'.format(self.history_data))
        return(access)


    def supportedOperatingModes(self) -> list:
        return( self.OPERATING_MODES )
 

    def isConnectedToPW(self) -> bool:
        return( self.authenticated())


   
    def tesla_battery_type(self, site_id) -> str:
        if site_id in self.site_info and isinstance(self.site_info[site_id], dict):
            info = self.site_info[site_id]
            comps = info.get('components', {}) if isinstance(info.get('components'), dict) else {}
            b_type = comps.get('battery_type') or info.get('battery_type')
            if b_type:
                return str(b_type).lower()
        return ''

    def tesla_gateway_type(self, site_id) -> str:
        if site_id in self.site_info and isinstance(self.site_info[site_id], dict):
            info = self.site_info[site_id]
            comps = info.get('components', {}) if isinstance(info.get('components'), dict) else {}
            g_type = comps.get('gateway_type') or info.get('gateway_type')
            if g_type:
                return str(g_type).lower()
        return ''

    def tesla_supports_local_access(self, site_id) -> bool:
        """Determines if the site uses Powerwall hardware supporting local customer LAN API."""
        b_type = self.tesla_battery_type(site_id)
        g_type = self.tesla_gateway_type(site_id)
        
        # Explicit PW3 / neop check: Powerwall 3 does not offer customer local API
        if 'powerwall3' in b_type or 'pw3' in b_type or 'pw3' in g_type or 'neop' in g_type:
            return False
            
        # Explicit Powerwall 2 / Backup Gateway detection
        if 'ac_powerwall' in b_type or 'powerwall2' in b_type or g_type in ('teg', 'gateway2', 'gateway1'):
            return True
            
        # Default for existing Powerwall battery installations if not explicitly PW3
        if site_id in self.site_info and isinstance(self.site_info[site_id], dict):
            comps = self.site_info[site_id].get('components', {})
            if isinstance(comps, dict) and comps.get('battery'):
                return True
                
        return False

    def teslaSolarInstalled(self, site_id) -> bool:
        return(self.site_info[site_id]['components']['solar'])

    def tesla_get_pw_name(self, site_id) -> str:
        return(self.site_info[site_id]['site_name'])

    def teslaExtractOperationMode(self, site_id):
        return(self.site_info[site_id]['default_real_mode'])

    def teslaExtractStormMode(self, site_id):
        return(self.site_live_info[site_id]['storm_mode_active'])

    def teslaExtractBackupPercent(self, site_id):
        logging.debug('teslaExtractBackupPercent : {} {}'.format(site_id, self.site_info))
        return(self.site_info[site_id]['backup_reserve_percent'])
    
    def tesla_total_battery(self, site_id):
        if site_id in self.site_live_info and isinstance(self.site_live_info[site_id], dict):
            return self.site_live_info[site_id].get('total_pack_energy')
        if isinstance(self.total_pack_energy, dict) and site_id in self.total_pack_energy:
            return self.total_pack_energy[site_id]
        return None
        
    def tesla_remaining_battery (self, site_id):
        return(self.site_live_info[site_id]['energy_left'])
    
    def tesla_island_staus(self, site_id):
        return(self.site_live_info[site_id]['island_status'])
    
    def tesla_grid_staus(self, site_id):
        return(self.site_live_info[site_id]['grid_status'])
    
    def tesla_live_grid_service_active(self, site_id):
        return(self.site_live_info[site_id]['grid_services_active'])

    def tesla_live_grid_power(self, site_id):
        return(self.site_live_info[site_id]['grid_power'])
    
    def tesla_live_generator_power(self, site_id):
        return(self.site_live_info[site_id]['generator_power'])
    
    def tesla_live_load_power(self, site_id):
        return(self.site_live_info[site_id]['load_power'])
    
    def tesla_live_battery_power(self, site_id):
        return(self.site_live_info[site_id]['battery_power'])
    
    def tesla_live_solar_power(self, site_id):
        logging.debug('Solar power : {} {}'.format(self.site_live_info[site_id]['solar_power'], self.site_live_info[site_id]))
        return(self.site_live_info[site_id]['solar_power'])

    def tesla_live_timestamp(self, site_id):
        if site_id in self.site_live_info and isinstance(self.site_live_info[site_id], dict):
            return self.site_live_info[site_id].get('timestamp')
        return None

    def teslaExtractTouMode(self, site_id):
        return(self.site_info[site_id]['tou_settings']['optimization_strategy'])

    def teslaExtractTouScheduleList(self, site_id):        
        self.touScheduleList = self.site_live_info[site_id]['components']['tou_settings']['schedule']
        return( self.touScheduleList )

    def teslaExtractChargeLevel(self, site_id):
        try:
            return(round(self.site_live_info[site_id]['percentage_charged'],2))
        except Exception as e:
            return(None) 
        
    #def teslaExtractBackoffLevel(self, site_id):
    #    return(round(self.site_info[site_id]['backup_reserve_percent'],1))

    def teslaExtractGridStatus(self, site_id): 
        return(self.site_live_info[site_id]['island_status'])
    
    def teslaExtractLoad(self, site_id): 
        return(self.site_live_info[site_id]['load_power'])

    def teslaExtractSolarSupply(self, site_id):
        return(self.site_live_info[site_id]['solar_power'])

    def teslaExtractBatterySupply(self, site_id):     
        return(self.site_live_info[site_id]['battery_power'])

    def teslaExtractGridSupply(self, site_id):     
        return(self.site_live_info[site_id]['grid_power'])

    def teslaExtractEnergyRemaining(self, site_id): 
        if site_id in self.site_live_info and isinstance(self.site_live_info[site_id], dict):
            if 'total_pack_energy' in self.site_live_info[site_id]:
                if isinstance(self.total_pack_energy, dict):
                    self.total_pack_energy[site_id] = self.site_live_info[site_id]['total_pack_energy']
            if 'energy_left' in self.site_live_info[site_id]:
                return self.site_live_info[site_id]['energy_left']
        if isinstance(self.total_pack_energy, dict) and site_id in self.total_pack_energy:
            val = self.total_pack_energy[site_id]
            if val != self.NaN:
                return val
        return None

    def teslaExtractGridImportMode(self, site_id):
        if site_id in self.site_info and isinstance(self.site_info[site_id], dict):
            disallow = self.site_info[site_id].get('disallow_charge_from_grid_with_solar_installed')
            if disallow is None and 'components' in self.site_info[site_id]:
                disallow = self.site_info[site_id]['components'].get('disallow_charge_from_grid_with_solar_installed')
            if disallow is not None:
                return 0 if disallow else 1
            return 1
        return None

    def teslaExtractGridExportMode(self, site_id):
        if site_id in self.site_info and isinstance(self.site_info[site_id], dict):
            rule = self.site_info[site_id].get('customer_preferred_export_rule')
            if rule is None and 'components' in self.site_info[site_id]:
                rule = self.site_info[site_id]['components'].get('customer_preferred_export_rule')
            if rule:
                rule_str = str(rule).strip().lower()
                if rule_str == 'pv_only':
                    return 0
                elif rule_str == 'battery_ok':
                    return 1
                elif rule_str == 'never':
                    return 2
        return None

    def teslaExtractEvChargeReserve(self, site_id):
        if site_id in self.site_info and isinstance(self.site_info[site_id], dict):
            pct = self.site_info[site_id].get('off_grid_vehicle_charging_reserve_percent')
            if pct is None and 'components' in self.site_info[site_id]:
                pct = self.site_info[site_id]['components'].get('off_grid_vehicle_charging_reserve_percent')
            if pct is not None:
                return int(pct)
        return None

    def teslaGet_backup_time_remaining(self, site_id):
        try:
            temp = self._callApi('GET', f'/energy_sites/{site_id}/backup_time_remaining')
            if temp and 'response' in temp and isinstance(temp['response'], dict):
                return temp['response'].get('time_remaining_hours')
        except Exception as e:
            logging.debug(f'teslaGet_backup_time_remaining error: {e}')
        return None

    def teslaGet_tariff_rate(self, site_id):
        try:
            temp = self._callApi('GET', f'/energy_sites/{site_id}/tariff_rate')
            if temp and 'response' in temp:
                return temp['response']
        except Exception as e:
            logging.debug(f'teslaGet_tariff_rate error: {e}')
        return None

    def TeslaGet_current_rate_state(self, site_id):
        try:
            temp = self._callApi('GET', f'/energy_sites/{site_id}/tariff_rate')
            if temp and 'response' in temp and isinstance(temp['response'], dict):
                return temp['response'].get('rate_plan')
        except Exception as e:
            logging.debug(f'TeslaGet_current_rate_state error: {e}')
        return None

    def teslaExtractGeneratorSupply (self, site_id):
        return(self.site_live_info[site_id]['generator_power'])

    def teslaExtractGridServiceActive(self, site_id):
        try:
            if self.site_live_info[site_id]['grid_services_enabled']:
                return(1)
            else:
                return(0)
        except:
            return(99)
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
    def tesla_grid_energy_import(self, site_id, day):
        if day in self.DAY_HISTORY:
            return self.history_data.get(site_id, {}).get('energy', {}).get(day, {}).get('grid_energy_imported', 0)
        return 0
        
    def tesla_grid_energy_export(self, site_id, day):    
        if day in self.DAY_HISTORY:
            d = self.history_data.get(site_id, {}).get('energy', {}).get(day, {})
            return (d.get('grid_energy_exported_from_solar', 0) +
                    d.get('grid_energy_exported_from_generator', 0) +
                    d.get('grid_energy_exported_from_battery', 0))
        return 0

    def tesla_solar_to_grid_energy(self, site_id, day): 
        if day in self.DAY_HISTORY:
            return self.history_data.get(site_id, {}).get('energy', {}).get(day, {}).get('grid_energy_exported_from_solar', 0)
        return 0

    def tesla_solar_energy_exported(self, site_id, day):
        if day in self.DAY_HISTORY:
            return self.history_data.get(site_id, {}).get('energy', {}).get(day, {}).get('solar_energy_exported', 0)
        return 0

    def tesla_home_energy_total(self, site_id, day):    
        if day in self.DAY_HISTORY:
            d = self.history_data.get(site_id, {}).get('energy', {}).get(day, {})
            return (d.get('consumer_energy_imported_from_grid', 0) +
                    d.get('consumer_energy_imported_from_solar', 0) +
                    d.get('consumer_energy_imported_from_battery', 0) +
                    d.get('consumer_energy_imported_from_generator', 0))
        return 0

    def tesla_home_energy_solar(self, site_id, day):   
        if day in self.DAY_HISTORY:
            return self.history_data.get(site_id, {}).get('energy', {}).get(day, {}).get('consumer_energy_imported_from_solar', 0)
        return 0
        
    def tesla_home_energy_battery(self, site_id, day):   
        if day in self.DAY_HISTORY:
            return self.history_data.get(site_id, {}).get('energy', {}).get(day, {}).get('consumer_energy_imported_from_battery', 0)
        return 0
        
    def tesla_home_energy_grid(self, site_id, day):   
        if day in self.DAY_HISTORY:
            return self.history_data.get(site_id, {}).get('energy', {}).get(day, {}).get('consumer_energy_imported_from_grid', 0)
        return 0

    def tesla_home_energy_generator(self, site_id, day):   
        if day in self.DAY_HISTORY:
            return self.history_data.get(site_id, {}).get('energy', {}).get(day, {}).get('consumer_energy_imported_from_generator', 0)
        return 0

    def tesla_battery_energy_import(self, site_id, day):        
        if day in self.DAY_HISTORY:
            d = self.history_data.get(site_id, {}).get('energy', {}).get(day, {})
            return (d.get('battery_energy_imported_from_grid', 0) +
                    d.get('battery_energy_imported_from_solar', 0) +
                    d.get('battery_energy_imported_from_generator', 0))
        return 0

    def tesla_battery_energy_export(self, site_id, day):
        if day in self.DAY_HISTORY:
            return self.history_data.get(site_id, {}).get('energy', {}).get(day, {}).get('battery_energy_exported', 0)
        return 0
        
    def tesla_grid_service_export(self, site_id, day):
        if day in self.DAY_HISTORY:
            return self.history_data.get(site_id, {}).get('energy', {}).get(day, {}).get('grid_services_energy_exported', 0)
        return 0

    def tesla_grid_service_import(self, site_id, day):
        if day in self.DAY_HISTORY:
            return self.history_data.get(site_id, {}).get('energy', {}).get(day, {}).get('grid_services_energy_imported', 0)
        return 0

    def tesla_backup_events(self, site_id, day):
        if day in self.DAY_HISTORY:
            return self.history_data.get(site_id, {}).get('backup', {}).get(day, {}).get('total_events', 0)
        return 0
        
    def tesla_backup_time(self, site_id, day):
        if day in self.DAY_HISTORY:
            return self.history_data.get(site_id, {}).get('backup', {}).get(day, {}).get('total_duration', 0)
        return 0

    def tesla_evcharge_power(self, site_id, day):
        if day in self.DAY_HISTORY:
            return self.history_data.get(site_id, {}).get('charge', {}).get(day, {}).get('total_energy', 0)
        return 0
        
    def tesla_evcharge_time(self, site_id, day):
        if day in self.DAY_HISTORY:
            return self.history_data.get(site_id, {}).get('charge', {}).get(day, {}).get('total_duration', 0)
        return 0



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