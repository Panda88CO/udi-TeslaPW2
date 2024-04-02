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
#from OLD.TeslaPWApi import TeslaPWApi



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

        self.TPWlocal = Powerwall(self.IPaddress)

        #logging.debug('self.TPWlocal - {}'.format(self.TPWlocal))
        self.TPWlocal.login(self.localPassword, self.localEmail)
        logging.debug('self.TPWlocal ')
        loginAttempts = 0
        #temp = self.TPWlocal.is_authenticated()
        #logging.debug('authendicated = {} '.format(temp))
        while not(self.TPWlocal.is_authenticated()) and loginAttempts < 10:            
            logging.info('Trying to log into Tesla Power Wall') 
            time.sleep(30)
            self.TPWlocal.login(self.localPassword, self.localEmail)
            loginAttempts = loginAttempts + 1
            self.localAccessUp = False
            if loginAttempts == 10: 
                logging.error('Local Loging failed after 10 attempts - check credentials.')
                logging.error('Powerwall may need to be turned on and off during this.  ')
                os.exit()
                break
        
        self.localAccessUp = True
        return(self.localAccessUp)



    def is_authendicated(self):
        return(self.TPWlocal.is_authenticated())


    def get_GWserial_number(self):
        logging.debug('Gateway: {}'.format(self.TPWlocal.get_gateway_din()))
        return(self.TPWlocal.get_gateway_din())



    def get_site_name(self):
        info = self.TPWlocal.get_site_info()
        return(str(info.site_name))