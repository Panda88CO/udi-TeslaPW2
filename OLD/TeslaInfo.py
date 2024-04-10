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
from tesla_powerwall import GridStatus, OperationMode, MeterType
#from OLD.TeslaPWApi import TeslaPWApi



class tesla_info(object):
    def __init__ (self,  PWlocal, PWcloud, site_id):
        logging.debug('class tesla_info - init')
        self.site_id = site_id
        self.TPWlocal = PWlocal
        self.TPWcloud = PWcloud
        self.generatorInstalled  = True # I have not found a way to identify this on clould only connection so it will report even if not there
        self.solarInstalled = False
        self.ISYCritical = {}
        self.lastDay = date.today()  
        self.localAccessUp = False
        self.cloudAccessUp = False
        self.TPWcloudAccess = PWcloud != None
        self.TPWlocalAccess = PWlocal != None
        self.systemReady = False 
        self.firstPollCompleted = False
        self.operationModeEnum = {0:'backup', 1:'self_consumption', 2:'autonomous', 3:'site_ctrl'}
        self.operationModeEnumList = ['backup','self_consumption', 'autonomous', 'site_ctrl']    
        #self.OPERATING_MODES = ["backup", "self_consumption", "autonomous"]
        self.TOU_MODES = ["economics", "balanced"]
        #\if not self.local_access_enabled() and not self.cloud_access_enabled():
        #    logging.debug('No connection specified')
        #logging.debug('Tesla_info before retrieving clould data')
        #logging.debug('oauthTokens: {}'.format(self.TPWcloud._oauthTokens))
        #if self.cloud_access_enabled():
        #    self.TPWcloud.tesla_get_site_info(self.site_id)
        #    self.TPWcloud.tesla_get_live_status(self.site_id)
        #    self.TPWcloud.tesla_get_today_history(self.site_id, 'energy')
        #    self.TPWcloud.tesla_get_yesterday_history(self.site_id, 'energy')
        #    logging.debug('Clould data retrieved tesla_info')


    def local_access_enabled(self):
        return(self.TPWlocal.local_access())
    
    def cloud_access_enabled(self):
        return(self.TPWcloud.cloud_access())
    

    def init_cloud(self):
        logging.debug('init_cloud')
        self.teslaCloudConnect()
        while not self.TPWcloud.authendicated():
            logging.info('Waiting for cloud access')
            time.sleep(5)       
        self.TPWcloudAccess = True
        self.cloudAccessUp = True
        self.TPWcloud.tesla_get_site_info(self.site_id) # needs to run first to get timezone name 
        self.TPWcloud.tesla_get_live_status(self.site_id)
        self.TPWcloud.tesla_get_today_history(self.site_id, 'energy')
        self.TPWcloud.tesla_get_today_history(self.site_id, 'backup')
        #self.TPWcloud.tesla_get_today_history(self.site_id, 'charge')
        self.TPWcloud.tesla_get_yesterday_history(self.site_id, 'energy')
        self.TPWcloud.tesla_get_yesterday_history(self.site_id, 'backup')
        #self.TPWcloud.tesla_get_yesterday_history(self.site_id, 'charge')
        logging.debug('Cloud data retrieved tesla_info')
        

    def init_local(self):
        logging.debug('init_local')
        self.gridStatusEnum = {GridStatus.CONNECTED.value: 'on_grid', GridStatus.ISLANDED_READY.value:'islanded_ready', GridStatus.ISLANDED.value:'islanded', GridStatus.TRANSITION_TO_GRID.value:'transition to grid' }
        self.operationLocalEnum =  {OperationMode.BACKUP.value:'backup',OperationMode.SELF_CONSUMPTION.value:'self_consumption', OperationMode.AUTONOMOUS.value:'autonomous', OperationMode.SITE_CONTROL.value: 'site_ctrl' }
        self.solarInstalled = False
        self.generatorInstalled = False
        try:
            meters = self.TPWlocal.get_meters()
            logging.debug(meters)
            installed_dev = meters.meters
            logging.debug('installed dev {}'.format(installed_dev))
            for tmp_meter in installed_dev:
                logging.debug('meter: {} '.format(tmp_meter))
                if 'generator' in tmp_meter.values():
                    self.generatorInstalled = True
                if 'solar' in tmp_meter.values():
                    self.solarInstalled = True
        except Exception as e:
            logging.debug('Exception {}'.format(e))
                              
        '''
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
        '''
        self.metersDayStart = meters
        if self.solarInstalled:
            self.DSsolarMeter = self.metersDayStart.get_meter(MeterType.SOLAR)
        self.DSbatteryMeter = self.metersDayStart.get_meter(MeterType.BATTERY)
        self.DSloadMeter = self.metersDayStart.get_meter(MeterType.LOAD)
        self.DSsiteMeter = self.metersDayStart.get_meter(MeterType.SITE)
        if self.generatorInstalled:
            self.DSgeneratorMeter = self.metersDayStart.get_meter(MeterType.GENERATOR)


    

    def teslaCloudConnect(self ):
        logging.debug('teslaCloudConnect {}'.format(self.TPWcloud))
        
        self.TPWcloudAccess = True
        if not(self.TPWcloud.authendicated()):
            logging.debug('Error connecting to Tesla Cloud - check refresh key')
            self.cloudAccessUp=False
            self.TPWcloudAccess = False
        else:
            logging.debug('Logged in Cloud - retrieving data')
            self.TPWcloudAccess = True
            self.cloudAccessUp = True
           

        return(self.cloudAccessUp)


    def teslaInitializeData(self):
        logging.debug('teslaInitializeData')
        if not(self.TPWcloudAccess):
            logging.debug ('no access to cloud data - starting accumulting from 0')
            self.yesterdayTotalSolar = 0
            self.yesterdayTotalConsumption = 0 
            self.yesterdayTotalGeneration  = 0 
            self.yesterdayTotalBattery =  0 
            self.yesterdayTotalGrid = 0
            self.yesterdayTotalGridServices = 0
            self.yesterdayTotalGenerator = 0
            self.daysTotalGridServices = 0 #Does not seem to exist
            self.daysTotalGenerator = 0 #needs to be updated - may not ex     
            self.daysTotalBattery_imp = 0
            self.daysTotalBattery_exp = 0
            self.daysTotalSite_imp = 0

        else:
            self.TPWcloud.teslaUpdateCloudData(self.site_id,'all')
            self.daysTotalSolarGeneration = self.TPWcloud.tesla_solar_energy_exported(self.site_id, 'today')
            self.daysTotalConsumption = self.TPWcloud.tesla_home_energy_total(self.site_id, 'today' )
            self.daysTotalGeneraton = self.TPWcloud.tesla_grid_energy_export(self.site_id, 'today')
            self.daysTotalBattery = self.TPWcloud.tesla_home_energy_battery(self.site_id, 'today')
            self.daysTotalGrid = self.TPWcloud.tesla_home_energy_grid(self.site_id, 'today')
            self.daysTotalGenerator = self.TPWcloud.tesla_home_energy_generator(self.site_id, 'today')
            self.daysTotalSolar = self.TPWcloud.tesla_home_energy_solar(self.site_id, 'today')                                                     
            self.daysTotalGridServices = self.TPWcloud.tesla_grid_service_export(self.site_id, 'today') - self.TPWcloud.tesla_grid_service_import(self.site_id, 'today') #
            self.yesterdayTotalSolarGeneration = self.TPWcloud.tesla_solar_energy_exported(self.site_id, 'yesterday')
            self.yesterdayTotalConsumption = self.TPWcloud.tesla_home_energy_total(self.site_id, 'yesterday' )
            self.yesterdayTotalGeneraton = self.TPWcloud.tesla_grid_energy_export(self.site_id, 'yesterday')
            self.yesterdayTotalBattery = self.TPWcloud.tesla_home_energy_battery(self.site_id, 'yesterday')
            self.yesterdayTotalGrid = self.TPWcloud.tesla_home_energy_grid(self.site_id, 'yesterday')
            self.yesterdayTotalGenerator = self.TPWcloud.tesla_home_energy_generator(self.site_id, 'yesterday')
            self.yesterdaTotalSolar = self.TPWcloud.tesla_home_energy_solar(self.site_id, 'yesterday')         
            self.yesterdayTotalGridServices = self.TPWcloud.tesla_grid_service_export(self.site_id, 'yesterday') - self.TPWcloud.tesla_grid_service_import(self.site_id, 'yesterday')#

        logging.debug('teslaInitializeData - 1 - grid status {} '.format(GridStatus))
        #self.OPERATING_MODES = ["backup", "self_consumption", "autonomous"]
        #self.TOU_MODES = ["economics", "balanced"]
        self.metersStart = True
        self.gridstatus = {'on_grid':0, 'islanded_ready':1, 'islanded':2, 'transition ot grid':3}
        
        self.ISYgridEnum = {}
        for key in self.gridstatus:
            self.ISYgridEnum[self.gridstatus [key]]= key
        #logging.debug('teslaInitializeData - 1.1 -  self.ISYgridEnum{} '.format( self.ISYgridEnum))
        #logging.debug('teslaInitializeData - 1.1 -  self.ISYgridEnum{} '.format( GridStatus.CONNECTED.value))
        #logging.debug('teslaInitializeData - 1.1 -  self.ISYgridEnum{} '.format( GridStatus.ISLANDED_READY.value))
        #logging.debug('teslaInitializeData - 1.1 -  self.ISYgridEnum{} '.format( OperationMode.BACKUP.value))
        #logging.debug('teslaInitializeData - 1.1 -  self.ISYgridEnum{} '.format( OperationMode.SELF_CONSUMPTION.value))
        #logging.debug('teslaInitializeData - 1.1 -  self.ISYgridEnum{} '.format( GridStatus.ISLANDED.value))

        #self.gridStatusEnum = {GridStatus.CONNECTED.value: 'on_grid', GridStatus.ISLANDED_READY.value:'islanded_ready', GridStatus.ISLANDED.value:'islanded', GridStatus.TRANSITION_TO_GRID.value:'transition to grid' }
        #self.operationLocalEnum =  {OperationMode.BACKUP.value:'backup',OperationMode.SELF_CONSUMPTION.value:'self_consumption', OperationMode.AUTONOMOUS.value:'autonomous', OperationMode.SITE_CONTROL.value: 'site_ctrl' }
        #self.operationModeEnum = {0:'backup', 1:'self_consumption', 2:'autonomous', 3:'site_ctrl'}
        #self.operationModeEnumList = ['backup','self_consumption', 'autonomous', 'site_ctrl']    
        '''
        self.ISYoperationModeEnum = {}
        logging.debug( ' self.ISYoperationModeEnum, operationModeEnum: {} {}'.format(self.ISYoperationModeEnum, self.operationModeEnum))
        for key in self.operationModeEnum:
            self.ISYoperationModeEnum[self.operationModeEnum[key]] = key

        self.operationCloudEnum = {}
        logging.debug('teslaInitializeData - 2')
        if self.TPWcloudAccess:
            ModeList = self.TPWcloud.supportedOperatingModes(self.site_id)

            for i in range(0,len(ModeList)):
                self.operationCloudEnum[i]= ModeList[i] 
            ModeList = self.ISYoperationModeEnum
            logging.debug( ' self.operationCloudEnum, modelist: {} {}'.format(self.operationCloudEnum, ModeList ))
            for  key in ModeList:
                self.operationCloudEnum[ModeList[key]]= key
            
            ModeList = self.TPWcloud.supportedTouModes(self.site_id)
            self.touCloudEnum = {}
            self.ISYtouEnum = {}

            logging.debug( ' self.touCloudEnum,ISYtouEnum, modelist: {} {} {}'.format(self.touCloudEnum ,self.ISYtouEnum,  ModeList ))
            for i in range(0,len(ModeList)):
                self.touCloudEnum[i]= ModeList[i]
                self.ISYtouEnum[ModeList[i]] = i
        else:
            ModeList=None
        '''

    '''
    Get the most current data. We get data from the cloud first, if cloud
    access is enable, because we'll want to overwrite it  with local data
    if local access is enabled.

    When this finishes, we should have current PW data data.
    '''
    def pollSystemData(self, level='all'):
        logging.debug('PollSystemData - ' + str(level))

        try:
            self.nowDay = date.today() 
            if (self.lastDay.day != self.nowDay.day): # we passed midnight
                self.yesterdayTotalSolar = self.daysTotalSolar
                self.yesterdayTotalConsumption = self.daysTotalConsumption
                self.yesterdayTotalGeneration  = self.daysTotalGeneraton
                self.yesterdayTotalBattery =  self.daysTotalBattery
                self.yesterdayTotalBattery_imp =  self.daysTotalBattery_imp
                self.yesterdayTotalBattery_exp =  self.daysTotalBattery_exp
                self.yesterdayTotalGrid = self.daysTotalGridServices
                self.yesterdayTotalGridServices = self.daysTotalGridServices
                self.yesterdayTotalGenerator = self.daysTotalGenerator
                self.yesterdayTotalSite_imp = self.daysTotalSite_imp
           
                if self.localAccessUp:
                    if self.TPWlocal.is_authenticated():
                        self.metersDayStart = self.TPWlocal.get_meters()
                        if self.solarInstalled:
                            self.DSsolarMeter = self.metersDayStart.get_meter(MeterType.SOLAR)
                        self.DSbatteryMeter = self.metersDayStart.get_meter(MeterType.BATTERY)
                        self.DSloadMeter = self.metersDayStart.get_meter(MeterType.LOAD)
                        self.DSsiteMeter = self.metersDayStart.get_meter(MeterType.SITE)
                        if self.generatorInstalled:
                            self.DSgeneratorMeter = self.metersDayStart.get_meter(MeterType.GENERATOR)

            # Get data from the cloud....
            if self.TPWcloudAccess:
                logging.debug('pollSystemData - CLOUD')
                self.cloudAccessUp = self.TPWcloud.teslaUpdateCloudData(self.site_id,level)
                if level == 'all':
                    self.daysTotalSolarGeneration = self.TPWcloud.tesla_solar_energy_exported(self.site_id, 'today')
                    self.daysTotalConsumption = self.TPWcloud.tesla_home_energy_total(self.site_id, 'today' )
                    self.daysTotalGeneraton = self.TPWcloud.tesla_grid_energy_export(self.site_id, 'today')
                    self.daysTotalBattery = self.TPWcloud.tesla_home_energy_battery(self.site_id, 'today')
                    self.daysTotalGrid = self.TPWcloud.tesla_home_energy_grid(self.site_id, 'today')
                    self.daysTotalGenerator = self.TPWcloud.tesla_home_energy_generator(self.site_id, 'today')
                    self.daysTotalSolar = self.TPWcloud.tesla_home_energy_solar(self.site_id, 'today')                                                     
                    self.daysTotalGridServices = self.TPWcloud.tesla_grid_service_export(self.site_id, 'today') - self.TPWcloud.tesla_grid_service_import(self.site_id, 'today') #
                    self.yesterdayTotalSolarGeneration = self.TPWcloud.tesla_solar_energy_exported(self.site_id, 'yesterday')
                    self.yesterdayTotalConsumption = self.TPWcloud.tesla_home_energy_total(self.site_id, 'yesterday' )
                    self.yesterdayTotalGeneraton = self.TPWcloud.tesla_grid_energy_export(self.site_id, 'yesterday')
                    self.yesterdayTotalBattery = self.TPWcloud.tesla_home_energy_battery(self.site_id, 'yesterday')
                    self.yesterdayTotalGrid = self.TPWcloud.tesla_home_energy_grid(self.site_id, 'yesterday')
                    self.yesterdayTotalGenerator = self.TPWcloud.tesla_home_energy_generator(self.site_id, 'yesterday')
                    self.yesterdaTotalSolar = self.TPWcloud.tesla_home_energy_solar(self.site_id, 'yesterday')         
                    self.yesterdayTotalGridServices = self.TPWcloud.tesla_grid_service_export(self.site_id, 'yesterday') - self.TPWcloud.tesla_grid_service_import(self.site_id, 'yesterday')#

            # Get data directly from PW....              
            if self.localAccessUp:
                self.status = self.TPWlocal.get_sitemaster()
                self.meters = self.TPWlocal.get_meters()
                if self.solarInstalled:
                    self.solarMeter = self.meters.get_meter(MeterType.SOLAR)
                self.batteryMeter = self.meters.get_meter(MeterType.BATTERY)
                self.loadMeter = self.meters.get_meter(MeterType.LOAD)
                self.siteMeter = self.meters.get_meter(MeterType.SITE)
                if self.generatorInstalled:
                    self.generatorMeter = self.meters.get_meter(MeterType.GENERATOR)
                if level == 'all':
                    # any of this that we got from the cloud calculations is
                    # overwritten here because local data takes priority
                    # Need to correlate to APP!!!!
                    self.daysTotalSolar =  (self.solarMeter.energy_exported - self.DSsolarMeter.energy_exported)
                    self.daysTotalConsumption = (self.loadMeter.energy_imported - self.DSloadMeter.energy_imported)
                    self.daysTotalGeneraton = (self.siteMeter.energy_exported - self.DSsiteMeter.energy_exported )
                    self.daysTotalSite_imp =self.siteMeter.energy_imported - self.DSsiteMeter.energy_imported
                    self.daysTotalBattery_exp =float(self.batteryMeter.energy_exported - self.DSbatteryMeter.energy_exported)
                    self.daysTotalBattery_imp = float(self.batteryMeter.energy_imported - self.DSbatteryMeter.energy_imported)
                    self.daysTotalBattery =  (self.daysTotalBattery_exp-self.daysTotalBattery )
                    
                    self.daysTotalGrid = -self.daysTotalConsumption - self.daysTotalGeneraton 
                    if not self.TPWcloudAccess:
                        self.daysTotalGridServices = 0.0 #Does not seem to exist
                        self.daysTotalGenerator = 0.0 #needs to be updated - may not exist
            self.firstPollCompleted = True
            return True

        except Exception as e:
            logging.error('Exception PollSystemData: '+  str(e))
            logging.error('problems extracting data from tesla power wall')
            # NEED To logout and log back in locally
            # Need to retrieve/renew token from cloud

        
    ''' *****************************************************************

    methods to retrieve data.  pollSystemData() is used to query the
    PW data.  Then use the methods below to access it.  If we have
    local access, then we'll use that data, otherwise we'll use data
    from the cloud.
    '''
    # Need to be imlemented 
    def isNodeServerUp(self):
        
        logging.debug('isNodeServerUp - called' )
        if self.cloudAccessUp == True:
            return(1)
        elif self.localAccessUp == True:
            self.localAccessUp = self.TPWlocal.is_authenticated()
            if self.localAccessUp:
                return(1)
        else:
            return(0)

    def TPW_updateMeter(self):
        self.pollSystemData('all')
        return


    def getTPW_energy_remaining(self):
        if self.cloudAccessUp:
            energy_remain = self.TPWcloud.teslaExtractEnergyRemaining(self.site_id)
        elif self.localAccessUp and self.firstPollCompleted:
            try:
                energy_remain = self.TPWlocal.get_energy()
            except Exception:

                return
        else:
            return
        return(energy_remain)

    def getTPW_chargeLevel(self):
        
        if self.cloudAccessUp:
            chargeLevel = self.TPWcloud.teslaExtractChargeLevel(self.site_id)
        elif self.localAccessUp and self.firstPollCompleted:
            try:
                chargeLevel = self.TPWlocal.get_charge()
            except Exception:
                return
        else:
            return

        logging.debug('getTPW_chargeLevel' + str(chargeLevel))
        return(chargeLevel)


    def getTPW_backoffLevel(self):

        if self.cloudAccessUp:
            backoffLevel=self.TPWcloud.teslaExtractBackupPercent(self.site_id)
        elif self.localAccessUp and self.firstPollCompleted:
            try:
                backoffLevel=self.TPWlocal.get_backup_reserve_percentage()
            except Exception:
                return
        else:
            return

        logging.debug('getTPW_backoffLevel' + str(backoffLevel))
    
        return(round(backoffLevel,1))
    


    '''
    def getBackupPercentISYVar(self, node):
        logging.debug('getBackupPercentISYVar')
        return(self.isyINFO.varToISY(node, self.backoffLevel))
    '''
    

    def setTPW_backoffLevel(self, backupPercent):
        logging.debug('setTPW_backoffLevel')
        return(self.TPWcloud.tesla_set_backup_percent(backupPercent))

    def getTPW_gridStatus(self):
        key = None
        if self.cloudAccessUp:
            key = self.TPWcloud.teslaExtractGridStatus(self.site_id)
        elif self.localAccessUp and self.firstPollCompleted:
            try:
                statusVal = self.TPWlocal.get_grid_status()
                if statusVal.value in self.gridStatusEnum:
                    key = self.gridStatusEnum[statusVal.value ]

                    #logging.debug(key)
            except Exception:
                return
        else:
            return

        if key in self.gridstatus:
            logging.debug('Grid status: {}'.format(key))
            return(self.gridstatus[key])
        else:
            logging.debug('Grid status UNKNOW code {}: return 99'.format(key))
            return



    def getTPW_solarSupply(self):
        if self.solarInstalled:
            if self.cloudAccessUp:
                solarPwr = self.TPWcloud.tesla_live_solar_power(self.site_id)
            elif  self.localAccessUp and self.firstPollCompleted:
                try:
                    #logging.debug(self.meters)
                    solarPwr = self.solarMeter.instant_power
                except Exception:
                    return
            else:
                return
            logging.debug('getTPW_solarSupply - ' + str(solarPwr))
            return(round(solarPwr/1000,2))
            #site_live
        else:
            return

    def getTPW_batterySupply(self):
        if self.cloudAccessUp:
            batteryPwr = self.TPWcloud.tesla_live_battery_power(self.site_id)
        elif  self.localAccessUp and self.firstPollCompleted:
            try:
                batteryPwr = self.batteryMeter.instant_power
            except Exception:
                return
        else:
            return
        logging.debug('getTPW_batterySupply' + str(batteryPwr))
        return(round(batteryPwr/1000,2))
 
    def getTPW_instant_solar(self):
        #nneed to find local
        if self.cloudAccessUp:
            gridPwr = self.TPWcloud.teslaExtractGridSupply(self.site_id)
        #elif
        else:
            return


        #site_live
    def getTPW_gridSupply(self):
        if self.cloudAccessUp:
            gridPwr = self.TPWcloud.tesla_live_grid_power(self.site_id)
        elif  self.localAccessUp and self.firstPollCompleted:
            try:
                gridPwr = self.siteMeter.instant_power
            except Exception:
                return
        else:
            return
        logging.debug('getTPW_gridSupply'+ str(gridPwr))            

        return(round(gridPwr/1000,2))


    def getTPW_load(self):
        if self.cloudAccessUp:
            loadPwr = self.TPWcloud.tesla_live_load_power(self.site_id)
        elif  self.localAccessUp and self.firstPollCompleted:
            try:
                loadPwr = self.loadMeter.instant_power
            except Exception:
                return
        else:
            loadPwr = None
        logging.debug('getTPW_load ' + str(loadPwr))
        return(round(loadPwr/1000,2))


    def getTPW_daysSolar(self):
        if self.cloudAccessUp:
            Pwr = self.TPWcloud.tesla_solar_energy_exported(self.site_id, 'today')
        elif  self.localAccessUp and self.firstPollCompleted:
            try:
                Pwr = self.daysTotalSolar
            except Exception:
                return
        else:
            return
        logging.debug('getTPW_daysSolar ' + str(Pwr))
        return(round(Pwr/1000,2))


    def getTPW_daysConsumption(self):
        if self.cloudAccessUp:
            Pwr = self.TPWcloud.tesla_home_energy_total(self.site_id, 'today')
        elif  self.localAccessUp and self.firstPollCompleted:
            Pwr = self.daysTotalConsumption
        else:
            return
        logging.debug('getTPW_daysConsumption ' + str(Pwr))
        return(round(Pwr/1000,2))

    def getTPW_daysGeneration(self):  #Need to check if this is what is wanted
        if self.cloudAccessUp:
            Pwr = self.TPWcloud.tesla_grid_energy_export(self.site_id, 'today')
        elif  self.localAccessUp and self.firstPollCompleted:
            Pwr = self.daysTotalGeneraton
        else:
            return
        logging.debug('getTPW_daysGeneration ' + str(Pwr))        
        return(round(Pwr/1000,2))

    def getTPW_daysBattery(self):  
        if self.cloudAccessUp:
            Pwr = self.TPWcloud.tesla_battery_energy_export(self.site_id, 'today') -self.TPWcloud.tesla_battery_energy_import(self.site_id, 'today')
        elif  self.localAccessUp and self.firstPollCompleted:
            Pwr = self.daysTotalBattery
        else:
            return
        logging.debug('getTPW_daysBattery ' + str(Pwr))
        return(round(Pwr/1000,2))

    def getTPW_daysBattery_export(self):  
        if self.cloudAccessUp:
            Pwr = self.TPWcloud.tesla_battery_energy_export(self.site_id, 'today') 
        elif  self.localAccessUp and self.firstPollCompleted:
            Pwr = self.batteryMeter.energy_exported - self.DSbatteryMeter.energy_exported
        else:
            return
        logging.debug('getTPW_daysBattery ' + str(Pwr))
        return(round(Pwr/1000,2))

    def getTPW_daysBattery_import(self): 
        if self.cloudAccessUp:
            Pwr = self.TPWcloud.tesla_battery_energy_import(self.site_id, 'today') 
        elif  self.localAccessUp and self.firstPollCompleted:
            Pwr = self.batteryMeter.energy_imported - self.DSbatteryMeter.energy_imported
            return
        logging.debug('getTPW_daysBattery ' + str(Pwr))
        return(round(Pwr/1000,2))

    def getTPW_daysGrid(self):  
        if self.cloudAccessUp:
            Pwr = self.TPWcloud.tesla_grid_energy_export(self.site_id, 'today') - self.TPWcloud.tesla_grid_energy_import(self.site_id, 'today') 
        elif  self.localAccessUp and self.firstPollCompleted:
            Pwr = self.daysTotalGrid
        else:
            return
        logging.debug('getTPW_daysBattery ' + str(Pwr))
        return(round(Pwr/1000,2))

    def getTPW_daysGrid_import(self):  
        if self.cloudAccessUp:
            Pwr = self.TPWcloud.tesla_grid_energy_import(self.site_id, 'today') 
        elif  self.localAccessUp and self.firstPollCompleted:
            Pwr = self.siteMeter.energy_imported - self.DSsiteMeter.energy_imported
        else:
            return
        logging.debug('getTPW_daysBattery ' + str(Pwr))
        return(round(Pwr/1000,2))

    def getTPW_daysGrid_export(self):  
        if self.cloudAccessUp:
            Pwr = self.TPWcloud.tesla_grid_energy_export(self.site_id, 'today') 
        elif  self.localAccessUp and self.firstPollCompleted:
            Pwr = self.siteMeter.energy_exported - self.DSsiteMeter.energy_exported
        else:
            return
        logging.debug('getTPW_daysBattery ' + str(Pwr))
        return(round(Pwr/1000,2))




    def getTPW_daysGridServicesUse(self):  
        if self.cloudAccessUp:
            Pwr = self.TPWcloud.tesla_grid_service_export(self.site_id, 'today') - self.TPWcloud.tesla_grid_service_import(self.site_id, 'today')
        elif  self.localAccessUp and self.firstPollCompleted:
            Pwr = self.daysTotalGridServices
        else:
            return
        logging.debug('getTPW_daysGridServicesUse ' + str(Pwr))

        return(round(Pwr/1000,2))

    def getTPW_daysGeneratorUse(self):  
        if self.generatorInstalled:
            if self.cloudAccessUp:
                Pwr = self.TPWcloud.tesla_home_energy_generator(self.site_id, 'today')
            elif  self.localAccessUp and self.firstPollCompleted:
                Pwr = self.daysTotalGenerator
            else:
                return           
        else:
           return
        return(round(Pwr/1000,2))

    def getTPW_yesterdaySolar(self):
        if self.cloudAccessUp:
            Pwr = self.TPWcloud.tesla_solar_energy_exported(self.site_id, 'yesterday')
        elif  self.localAccessUp and self.firstPollCompleted:
            Pwr = self.yesterdayTotalSolar
        else:
            return
        logging.debug('getTPW_daysSolar ' + str(Pwr))
        return(round(Pwr/1000,2))

    def getTPW_yesterdayConsumption(self):
        if self.cloudAccessUp:
            Pwr = self.TPWcloud.tesla_home_energy_total(self.site_id, 'yesterday')
        elif  self.localAccessUp and self.firstPollCompleted:
            Pwr = self.yesterdayTotalConsumption
        else:
            return
        logging.debug('getTPW_daysConsumption ' + str(Pwr))
        return(round(Pwr/1000,2))

    def getTPW_yesterdayGeneration(self):  
        if self.cloudAccessUp:
            Pwr = self.TPWcloud.tesla_grid_energy_export(self.site_id, 'yesterday')
        elif  self.localAccessUp and self.firstPollCompleted:
            Pwr = self.yesterdayTotalGeneration
        else:
            return
        logging.debug('getTPW_daysGeneration ' + str(Pwr))
        return(round(Pwr/1000,2))

    def getTPW_yesterdayBattery(self):  

        if self.cloudAccessUp:
            Pwr = self.TPWcloud.tesla_battery_energy_export(self.site_id, 'yesterday') -self.TPWcloud.tesla_battery_energy_import(self.site_id, 'yesterday')
        elif  self.localAccessUp and self.firstPollCompleted:
            Pwr = self.yesterdayTotalBattery
        else:
            return
        logging.debug('getTPW_daysBattery ' + str(Pwr))
        return(round(Pwr/1000,2))
    def getTPW_yesterdayBattery_export(self):  
        if self.cloudAccessUp:
            Pwr = self.TPWcloud.tesla_battery_energy_export(self.site_id, 'yesterday') 
        elif  self.localAccessUp and self.firstPollCompleted:
            Pwr = self.yesterdayTotalBattery_exp
        else:
            return
        logging.debug('getTPW_daysBattery ' + str(Pwr))
        return(round(Pwr/1000,2))

    def getTPW_yesterdasBattery_import(self): 
        if self.cloudAccessUp:
            Pwr = self.TPWcloud.tesla_battery_energy_import(self.site_id, 'yesterday') 
        elif  self.localAccessUp and self.firstPollCompleted:
            Pwr = self.yesterdayTotalBattery_imp
            return
        logging.debug('getTPW_daysBattery ' + str(Pwr))
        return(round(Pwr/1000,2))
    

    def getTPW_yesterdayGrid(self):  

        if self.cloudAccessUp:
            Pwr = self.TPWcloud.tesla_grid_energy_export(self.site_id, 'yesterday') - self.TPWcloud.tesla_grid_energy_import(self.site_id, 'yesterday') 
        elif  self.localAccessUp and self.firstPollCompleted:
            Pwr = self.yesterdayTotalGrid
        else:
            return
        logging.debug('getTPW_daysBattery ' + str(Pwr))
        return(round(Pwr/1000,2))

    def getTPW_yesterdayGrid_import(self):  

        if self.cloudAccessUp:
            Pwr = self.TPWcloud.tesla_grid_energy_import(self.site_id, 'yesterday') 
        elif  self.localAccessUp and self.firstPollCompleted:
            Pwr = self.yesterdayTotalSite_imp
        else:
            return
        logging.debug('getTPW_daysBattery ' + str(Pwr))
        return(round(Pwr/1000,2))
    
    def getTPW_yesterdayGrid_export(self):  

        if self.cloudAccessUp:
            Pwr = self.TPWcloud.tesla_grid_energy_export(self.site_id, 'yesterday') - self.TPWcloud.tesla_grid_energy_import(self.site_id, 'yesterday') 
        elif  self.localAccessUp and self.firstPollCompleted:
            Pwr = self.yesterdayTotalGeneraton
        else:
            return
        logging.debug('getTPW_daysBattery ' + str(Pwr))
        return(round(Pwr/1000,2))

    def getTPW_yesterdayGridServicesUse(self):  

        if self.cloudAccessUp:
            Pwr = self.TPWcloud.tesla_grid_service_export(self.site_id, 'yesterday') - self.TPWcloud.tesla_grid_service_import(self.site_id, 'yesterday')
        elif  self.localAccessUp and self.firstPollCompleted:
            Pwr = self.yesterdayTotalGridServices
        else:
            return
        logging.debug('getTPW_daysGridServicesUse ' + str(Pwr))            
        return(round(Pwr/1000,2))
        #bat_history

    def getTPW_yesterdayGeneratorUse(self):  

        if self.cloudAccessUp:
            Pwr = self.TPWcloud.tesla_home_energy_generator(self.site_id, 'yesterday')
        elif  self.localAccessUp and self.firstPollCompleted:
            Pwr = self.yesterdayTotalGenerator
        else:
            return
        logging.debug('getTPW_daysGeneratorUse ' + str(Pwr))
        return(round(Pwr/1000,2))
        #bat_history


    def getTPW_operationMode(self):

        if self.cloudAccessUp:
            key = self.TPWcloud.teslaExtractOperationMode(self.site_id)
        elif  self.localAccessUp and self.firstPollCompleted:
            operationVal = self.TPWlocal.get_operation_mode()
            key = self.operationLocalEnum[operationVal.value]
        else:
            return
        logging.debug('getTPW_operationMode ' + str(key)) 
        return( self.operationModeEnumList.index(key))
    
    def setTPW_operationMode(self, index):
        logging.debug('setTPW_operationMode ')  
        return(self.TPWcloud.teslaSetOperationMode(self.operationModeEnumList[index]))

    ''' 
    def getTPW_running(self):
        if  self.TPWlocal.running:  
           return(1)   
        else:
           return(0)
    '''

    def getTPW_powerSupplyMode(self):
        logging.debug('getTPW_powerSupplyMode ')  
        logging.debug(self.status)
        if  self.status.is_power_supply_mode:
           return(1)   
        else:
           return(0)            
    
    def getTPW_ConnectedTesla(self):  # can check other direction 
        logging.debug('getTPW_ConnectedTesla ')  
        logging.debug(self.status)
        if self.status.is_connected_to_tesla:
            return(1)   
        else:
            return(0)

    def getTPW_onLine(self):
        logging.debug('getTPW_onLine') 
        if  self.localAccessUp and self.firstPollCompleted:
            return(self.getTPW_ConnectedTesla())
        else:
            if self.TPWcloudAccess:
                return(1)
            else:
                return(0)

    def getTPW_gridServiceActive(self):
        logging.debug('getTPW_gridServiceActive ')  
        if self.cloudAccessUp:
            res = self.TPWcloud.teslaExtractGridServiceActive(self.site_id)
        elif  self.localAccessUp and self.firstPollCompleted:
            res = self.TPWlocal.is_grid_services_active()   
        else:
            return
        if res:
            return(1)
        else:
            return (0)

    def getTPW_stormMode(self):
        logging.debug('getTPW_stormMode ')  
        if self.TPWcloudAccess:
            if self.TPWcloud.teslaExtractStormMode(self.site_id):
                return (1)
            else:
                return(0)

    def tesla_set_storm_mode(self, mode):
        logging.debug('getTPW_stormMode ')  
        return(self.TPWcloud.tesla_set_storm_mode(mode==1))

    def getTPW_touMode(self):
        logging.debug('getTPW_touMode ')  
        tmp = self.TPWcloud.teslaExtractTouMode(self.site_id)
        for indx in range(0,len(self.TOU_MODES)):
            if self.TOU_MODES[indx] == tmp:
                return(indx)
        return(99)

    def getTPW_touSchedule(self):
        logging.debug('getTPW_touSchedule ')  
        if self.TPWcloudAccess:        
            return(self.TPWcloud.teslaExtractTouScheduleList(self.site_id))


    #def setTPW_touMode(self, index):
    #    logging.debug('setTPW_touMode ')  
    #    if self.TPWcloudAccess:        
    #        return(self.TPWcloud.teslaSetTimeOfUseMode(self.touCloudEnum[index]))


    def setTPW_touSchedule(self, peakOffpeak, weekWeekend, startEnd, time_s):
        logging.debug('setTPW_touSchedule ')  
        if self.TPWcloudAccess:        
            return(self.TPWcloud.teslaSetTouSchedule( peakOffpeak, weekWeekend, startEnd, time_s))

    def setTPW_updateTouSchedule(self, peakOffpeak, weekWeekend, startEnd, time_s):
        logging.debug('setTPW_updateTouSchedule ')  
        if self.TPWcloudAccess:        
            return(self.TPWcloud.teslaSetTouSchedule( peakOffpeak, weekWeekend, startEnd, time_s))

    def getTPW_getTouData(self, days, peakMode, startEnd ):
        logging.debug('getTPW_getTouData ')
        if self.TPWcloudAccess:        
            return(self.TPWcloud.teslaExtractTouTime(days, peakMode, startEnd ))

    def getTPW_backup_time_remaining(self):
        return(self.TPWcloud.teslaGet_backup_time_remaining(self.site_id))

    def getTPW_tariff_rate(self):
        return(self.TPWcloud.teslaGet_tariff_rate(self.site_id))

    def getTPW_tariff_rate_state(self):
        return(self.TPWcloud.TeslaGet_current_rate_state(self.site_id))

    def disconnectTPW(self):
        logging.debug('disconnectTPW ')  
        if self.localAccessUp:
            self.TPWlocal.close()



    def getTPW_days_backup_events(self):
        try:
            return(self.TPWcloud.tesla_backup_events(self.site_id, 'today'))
        except Exception:
            return
        
    def getTPW_yesterday_backup_events(self):
        try:
            return(self.TPWcloud.tesla_backup_events(self.site_id, 'yesterday'))
        except Exception:
            return
        
    def getTPW_days_backup_time(self):
        try:
            return(self.TPWcloud.tesla_backup_time(self.site_id, 'today'))
        except Exception:
            return
            
    def getTPW_yesterday_backup_time(self):
        try:
            return(self.TPWcloud.tesla_backup_time(self.site_id, 'yesterday'))       
        except Exception:
            return
        
    def getTPW_days_evcharge_power(self):
        try:
            return(self.TPWcloud.tesla_evcharge_power(self.site_id, 'today'))
        except Exception:
            return
            
    def getTPW_yesterday_evcharge_power(self):
        try:
            return(self.TPWcloud.tesla_evcharge_power(self.site_id, 'yesterday'))
        except Exception:
            return
        
    def getTPW_days_evcharge_time(self):
        try:
            return(self.TPWcloud.tesla_evcharge_time(self.site_id, 'today'))
        except Exception:
            return
            
    def getTPW_yesterday_evcharge_time(self):
        try:
            return(self.TPWcloud.tesla_evcharge_time(self.site_id, 'yesterday'))           
        except Exception:
            return       


    def setTPW_yesterday_evcharge_time(self, imp_mode, exp_mode):
        try:
            return(self.TPWcloud.tesla_set_grid_import_export(self.site_id, imp_mode==1, exp_mode))           
        except Exception:
            return               
        
    def set_EV_charge_reserve(self, percent):
        try:
            return(self.TPWcloud.tesla_set_off_grid_vehicle_charging(self.site_id, percent))           
        except Exception:
            return               