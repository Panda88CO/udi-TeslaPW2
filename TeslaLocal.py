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
        self.gridStatusEnum = {GridStatus.CONNECTED.value: 'on_grid', GridStatus.ISLANDED_READY.value:'islanded_ready', GridStatus.ISLANDED.value:'islanded', GridStatus.TRANSITION_TO_GRID.value:'transition to grid' }
        self.operationLocalEnum =  {OperationMode.BACKUP.value:'backup',OperationMode.SELF_CONSUMPTION.value:'self_consumption', OperationMode.AUTONOMOUS.value:'autonomous', OperationMode.SITE_CONTROL.value: 'site_ctrl' }

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
        try:
            #self.gateway_id = self.TWPlocal.get_gateway_din()
            generator  = self.TPWlocal._api.get('generators')
            logging.debug('generator {}'.format(generator))
            if 'generators' in generator:
                if not(generator['generators']):
                    self.generatorInstalled = False
                else:
                    self.generatorInstalled = True
            else:
                self.generatorInstalled = False
        except Exception as e:
            self.generatorInstalled = False
            logging.error('Generator does not seem to be supported: {}'.format(e))
            
        solarInfo = self.TPWlocal.get_solars()
        logging.debug('solarInfo {}'.format(solarInfo))
        solar = len(solarInfo) != 0
        logging.debug('Test if solar installed ' + str(solar))
        if solar:
            self.solarInstalled = True
            logging.debug('Solar installed ' + str(solar))
        else:
            self.solarInstalled = False
        self.metersDayStart = self.TPWlocal.get_meters()
        if self.solarInstalled:
            self.DSsolarMeter = self.metersDayStart.get_meter(MeterType.SOLAR)
        self.DSbatteryMeter = self.metersDayStart.get_meter(MeterType.BATTERY)
        self.DSloadMeter = self.metersDayStart.get_meter(MeterType.LOAD)
        self.DSsiteMeter = self.metersDayStart.get_meter(MeterType.SITE)
        if self.generatorInstalled:
            self.DSgeneratorMeter = self.metersDayStart.get_meter(MeterType.GENERATOR)

        return(self.localAccessUp)



    def is_authendicated(self):
        return(self.TPWlocal.is_authenticated())


    def get_GWserial_number(self):
        logging.debug('Batteries: {}'.format(self.TPWlocal.get_batteries()))
        logging.debug('Gateway: {}'.format(self.TPWlocal.get_gateway_din()))
        return(self.TPWlocal.get_gateway_din())



    def get_site_name(self):
        info = self.TPWlocal.get_site_info()
        return(str(info.site_name))