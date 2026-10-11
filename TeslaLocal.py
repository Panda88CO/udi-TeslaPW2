#!/usr/bin/env python3

try:
    import udi_interface
    logging = udi_interface.LOGGER
    Custom = udi_interface.Custom
except ImportError:
    import logging
    logging.basicConfig(level=30)

from datetime import date
import time
import os
from tesla_powerwall import Powerwall, GridStatus, OperationMode, MeterType




class tesla_local:
    def __init__ (self, email, password, ip_address ):
   
        logging.debug('class tesla_info - init')

        self.generatorInstalled  = True # I have not found a way to identify this on clould only connection so it will report even if not there
        self.solarInstalled = False
        self.ISYCritical = {}
        self.lastDay = date.today()  
        self.localAccessUp = False
        self.TPWcloudAccess = False
        self.systemReady = False 
        self.firstPollCompleted = False

        self.localEmail = email
        self.localPassword = password
        self.IPaddress =  ip_address

        #self.local_access_enabled = my_Tesla_PW.local_access()
        #self.cloud_access_enabled = my_Tesla_PW.cloud_access()
        self.operationModeEnum = {0:'backup', 1:'self_consumption', 2:'autonomous', 3:'site_ctrl'}
        self.operationModeEnumList = ['backup','self_consumption', 'autonomous', 'site_ctrl']    
        #self.OPERATING_MODES = ["backup", "self_consumption", "autonomous"]
        #self.TOU_MODES = ["economics", "balanced"]




    def loginLocal (self):
        logging.debug('Local Access Supported')

        try:
            self.PWlocal = Powerwall(self.IPaddress)
            self.PWlocal.login(self.localPassword, self.localEmail)
        except Exception as e:
            logging.error(f'Initial local login attempt error: {e}')

        loginAttempts = 0
        while not self.is_authenticated() and loginAttempts < 3:            
            logging.info('Trying to log into Tesla Power Wall locally') 
            time.sleep(2)
            try:
                self.PWlocal.login(self.localPassword, self.localEmail)
            except Exception as e:
                logging.error(f'Local login retry failed: {e}')
            loginAttempts = loginAttempts + 1
            self.localAccessUp = False
            if loginAttempts >= 3: 
                logging.error('Local Login failed after 3 attempts - check credentials and gateway IP.')
                self.localAccessUp = False
                return False
        
        self.localAccessUp = self.is_authenticated()
        return(self.localAccessUp)

    def is_authenticated(self):
        if hasattr(self, 'PWlocal') and self.PWlocal is not None:
            try:
                return bool(self.PWlocal.is_authenticated())
            except Exception as e:
                logging.debug(f'Error checking local authentication: {e}')
                return False
        return False


    def get_GWserial_number(self):
        logging.debug('Gateway: {}'.format(self.PWlocal.get_gateway_din()))
        return(self.PWlocal.get_gateway_din())

    def get_meters(self):
        return(self.PWlocal.get_meters())

    def get_site_name(self):
        info = self.PWlocal.get_site_info()
        return(str(info.site_name))
    
    def get_backup_reserve_percentage(self):
        return(self.PWlocal.get_backup_reserve_percentage())
            
    def get_sitemaster(self):
        return(self.PWlocal.get_sitemaster())

    def get_energy(self):
        return(self.PWlocal.get_energy())
    
    def get_charge(self):
        return(self.PWlocal.get_charge())

    def get_grid_status(self):
        return(self.PWlocal.get_grid_status())
    
    def get_operation_mode(self):
        return(self.PWlocal.get_operation_mode())

    #def running(self):
    #    if  (self.PWlocal.running()):  
    #        return(1)   
    #    else:
    #       return(0)
    
    def is_grid_services_active(self):
        return(self.PWlocal.is_grid_services_active())
    
    def logout(self):
        if self.is_authenticated():
            self.PWlocal.logout()
