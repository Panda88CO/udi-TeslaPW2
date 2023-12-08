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
from tesla_powerwall import Powerwall, GridStatus, OperationMode, MeterType
from TeslaPWApi import TeslaPWApi



class tesla_info:
    def __init__ (self,  ISYname, ISY_Id, local, cloud):
        self.TEST = False

        logging.debug('class tesla_info - init')
        self.TPWcloud = None
        self.localPassword = ''
        self.localEmail = ''
        self.IPAddress = ''
        self.cloudEmail = ''
        self.cloudPassword = ''
        self.controllerID = ISY_Id
        self.controllerName = ISYname
        self.captchaMethod = ''
        self.captchaCode = ''
        self.captchaAPIKey = ''
        self.generatorInstalled  = True # I have not found a way to identify this on clould only connection so it will report even if not there
        self.solarInstalled = False
        self.ISYCritical = {}
        self.localAccessUp = False
        self.cloudAccessUp = False
        self.lastDay = date.today()  
        self.TPWlocalAccess = local
        self.TPWcloudAccess = cloud
        self.systemReady = False 

        if not local and not cloud:
            logging.debug('No connection specified')


    def loginLocal (self, email, password, IPaddress):
        self.localEmail = email
        self.localPassword = password
        self.IPAddress = IPaddress
        logging.debug('Local Access Supported')

        self.TPWlocal = Powerwall(IPaddress)
        self.TPWlocal.login(self.localPassword, self.localEmail)
        loginAttempts = 0
        while not(self.TPWlocal.is_authenticated()) and loginAttempts < 10:            
            logging.info('Trying to togging into Tesla Power Wall') 
            time.sleep(30)
            self.TPWlocal.login(self.localPassword, self.localEmail)
            loginAttempts = loginAttempts + 1
            self.localAccessUp = False 
            if loginAttempts == 10: 
                logging.error('Local Loging failed after 10 attempts - check credentials.')
                logging.error('Powerwall may need to be turned on and off during this.  ')
        else:
            self.localAccessUp = True
            generator  = self.TPWlocal._api.get('generators')
            if not(generator['generators']):
                self.generatorInstalled = False
            else:
                self.generatorInstalled = True
            solarInfo = self.TPWlocal.get_solars()
            solar = len(solarInfo) != 0
            logging.debug('Test Solar instlled ' + str(solar))
            if solar:
                self.solarInstalled = True
                logging.debug('Solar instlled ' + str(solar))
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



    #def loginCloud(self, email, password ):
    ##    self.cloudEmail = email
    #    self.cloudPassword = password
    #    #self.captchaAPIKey = captchaAPIkey

    #    logging.debug('Cloud Access Supported')
    #    self.TPWcloud = TeslaCloudAPI(self.cloudEmail, self.cloudPassword)
    #    self.TPWcloudAccess = True
           
    

    def getRtoken(self):
        return(self.TPWcloud.getRtoken())

    def teslaCloudConnect(self, Rtoken ):
        logging.debug('teslaCloudConnect')
        self.TPWcloud = TeslaPWApi(Rtoken)
        self.TPWcloudAccess = True
        if not(self.TPWcloud.isConnectedToEV()):    
            logging.debug('Error connecting to Tesla Could - check refresh key')
            self.cloudAccessUp=False
            self.TPWcloudAccess = False
        else:
            logging.debug('Logged in Cloud - retrieving data')
            self.TPWcloudAccess = True
            self.TPWcloud.teslaCloudInfo()
            self.TPWcloud.teslaRetrieveCloudData()
            self.solarInstalled = self.TPWcloud.teslaGetSolar()
            self.cloudAccessUp
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
        else:
            self.TPWcloud.teslaUpdateCloudData('all')
            self.daysTotalSolar = self.TPWcloud.teslaExtractDaysSolar()
            self.daysTotalConsumption = self.TPWcloud.teslaExtractDaysConsumption()
            self.daysTotalGeneraton = self.TPWcloud.teslaExtractDaysGeneration()
            self.daysTotalBattery = self.TPWcloud.teslaExtractDaysBattery()
            self.daysTotalGenerator = self.TPWcloud.teslaExtractDaysGeneratorUse()
            self.daysTotalGridServices = self.TPWcloud.teslaExtractDaysGridServicesUse()
            self.yesterdayTotalSolar = self.TPWcloud.teslaExtractYesteraySolar()
            self.yesterdayTotalConsumption = self.TPWcloud.teslaExtractYesterdayConsumption()
            self.yesterdayTotalGeneration  = self.TPWcloud.teslaExtractYesterdayGeneraton()
            self.yesterdayTotalBattery =  self.TPWcloud.teslaExtractYesterdayBattery() 
            self.yesterdayTotalGridServices = self.TPWcloud.teslaExtractYesterdayGridServiceUse()
            self.yesterdayTotalGenerator = self.TPWcloud.teslaExtractYesterdayGeneratorUse()

           
        #self.OPERATING_MODES = ["backup", "self_consumption", "autonomous"]
        #self.TOU_MODES = ["economics", "balanced"]
        self.metersStart = True
        self.gridstatus = {'on_grid':0, 'islanded_ready':1, 'islanded':2, 'transition ot grid':3}
        
        self.ISYgridEnum = {}
        for key in self.gridstatus:
            self.ISYgridEnum[self.gridstatus [key]]= key

        self.gridStatusEnum = {GridStatus.CONNECTED.value: 'on_grid', GridStatus.ISLANEDED_READY.value:'islanded_ready', GridStatus.ISLANEDED.value:'islanded', GridStatus.TRANSITION_TO_GRID.value:'transition ot grid' }
        self.operationLocalEnum =  {OperationMode.BACKUP.value:'backup',OperationMode.SELF_CONSUMPTION.value:'self_consumption', OperationMode.AUTONOMOUS.value:'autonomous', OperationMode.SITE_CONTROL.value: 'site_ctrl' }
        self.operationModeEnum = {0:'backup', 1:'self_consumption', 2:'autonomous', 3:'site_ctrl'}
        self.ISYoperationModeEnum = {}
        for key in self.operationModeEnum:
            self.ISYoperationModeEnum[self.operationModeEnum[key]] = key

        self.operationCloudEnum = {}  

        if self.TPWcloudAccess:
            ModeList = self.TPWcloud.supportedOperatingModes()
            for i in range(0,len(ModeList)):
                self.operationCloudEnum[i]= ModeList[i] 
            ModeList = self.ISYoperationModeEnum

            for  key in ModeList:
                self.operationCloudEnum[ModeList[key]]= key
            
            ModeList = self.TPWcloud.supportedTouModes()
            self.touCloudEnum = {}
            self.ISYtouEnum = {}
            for i in range(0,len(ModeList)):
                self.touCloudEnum[i]= ModeList[i]
                self.ISYtouEnum[ModeList[i]] = i
        else:
            ModeList=None
        

    '''
    def storeDaysData(self, filename, solar, consumption, generation, battery, gridUse, generator, dayInfo ):
        try:
            if not(os.path.exists('./dailyData')):
                os.mkdir('./dailyData')
                dataFile = open('./dailyData/'+filename, 'w+')
                dataFile.write('Date, solarKW, ConsumptionKW, GenerationKW, BatteryKW, GridServicesUseKW, GeneratorKW \n')
                dataFile.close()
            dataFile = open('./dailyData/'+filename, 'a')
            dataFile.write(str(dayInfo)+ ','+str(solar)+','+str(consumption)+','+str(generation)+','+str(battery)+','+str(gridUse)+','+str(generator)+'\n')
            dataFile.close()
        except Exception as e:
            logging.error('Exception storeDaysData: '+  str(e))         
            logging.error ('Failed to add data to '+str(filename))
    '''    

    '''
    Get the most current data. We get data from the cloud first, if cloud
    access is enable, because we'll want to overwrite it  with local data
    if local access is enabled.

    When this finishes, we should have current PW data data.
    '''
    def pollSystemData(self, level):
        logging.debug('PollSystemData - ' + str(level))

        try:
            self.nowDay = date.today() 
            if (self.lastDay.day != self.nowDay.day) or self.TEST: # we passed midnight
                self.yesterdayTotalSolar = self.daysTotalSolar
                self.yesterdayTotalConsumption = self.daysTotalConsumption
                self.yesterdayTotalGeneration  = self.daysTotalGeneraton
                self.yesterdayTotalBattery =  self.daysTotalBattery 
                self.yesterdayTotalGrid = self.daysTotalGrid
                self.yesterdayTotalGridServices = self.daysTotalGridServices
                self.yesterdayTotalGenerator = self.daysTotalGenerator
                if self.TPWlocalAccess:
                    self.metersDayStart = self.TPWlocal.get_meters()
                    if self.solarInstalled:
                        self.DSsolarMeter = self.metersDayStart.get_meter(MeterType.SOLAR)
                    self.DSbatteryMeter = self.metersDayStart.get_meter(MeterType.BATTERY)
                    self.DSloadMeter = self.metersDayStart.get_meter(MeterType.LOAD)
                    self.DSsiteMeter = self.metersDayStart.get_meter(MeterType.SITE)
                    if self.generatorInstalled:
                        self.DSgeneratorMeter = self.metersDayStart.get_meter(MeterType.GENERATOR)
                self.lastDay = self.nowDay

            
            # Get data from the cloud....
            if self.TPWcloudAccess:
                logging.debug('pollSystemData - CLOUD')
                self.cloudAccessUp = self.TPWcloud.teslaUpdateCloudData(level)
                if level == 'all':
                    self.daysTotalSolar = self.TPWcloud.teslaExtractDaysSolar()
                    self.daysTotalConsumption = self.TPWcloud.teslaExtractDaysConsumption()
                    self.daysTotalGeneraton = self.TPWcloud.teslaExtractDaysGeneration()
                    self.daysTotalBattery = self.TPWcloud.teslaExtractDaysBattery()
                    self.daysTotalGrid = self.TPWcloud.teslaExtractDaysGrid()
                    self.daysTotalGenerator = self.TPWcloud.teslaExtractDaysGeneratorUse()
                    self.daysTotalGridServices = self.TPWcloud.teslaExtractDaysGridServicesUse()
                    self.yesterdayTotalSolar = self.TPWcloud.teslaExtractYesteraySolar()
                    self.yesterdayTotalConsumption = self.TPWcloud.teslaExtractYesterdayConsumption()
                    self.yesterdayTotalGeneration  = self.TPWcloud.teslaExtractYesterdayGeneraton()
                    self.yesterdayTotalBattery =  self.TPWcloud.teslaExtractYesterdayBattery() 
                    self.yesterdayTotalGrid =  self.TPWcloud.teslaExtractYesterdayGrid() 
                    self.yesterdayTotalGridServices = self.TPWcloud.teslaExtractYesterdayGridServiceUse()
                    self.yesterdayTotalGenerator = self.TPWcloud.teslaExtractYesterdayGeneratorUse()          

            # Get data directly from PW....
            if self.TPWlocalAccess:
                logging.debug('pollSystemData - local - local connection = {}'.format(self.localAccessUp))
                if not self.TPWlocal.is_authenticated():
                    self.TPWlocal.logout()
                    time.sleep(1)
                    self.loginLocal(self.localEmail, self.localPassword, self.IPAddress)
                    if not self.TPWlocal.is_authenticated():
                        self.localAccessUp = False
                        logging.error('No connection to Local Tesla Power Wall')
                        return False

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
                    self.daysTotalBattery =  (float(self.batteryMeter.energy_exported - self.DSbatteryMeter.energy_exported - 
                                                (self.batteryMeter.energy_imported - self.DSbatteryMeter.energy_imported)))
                    
                    self.daysTotalGrid = -self.daysTotalConsumption - self.daysTotalGeneraton 
                    if not self.TPWcloudAccess:
                        self.daysTotalGridServices = 0.0 #Does not seem to exist
                        self.daysTotalGenerator = 0.0 #needs to be updated - may not exist

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
        if self.localAccessUp == True or self.cloudAccessUp == True:
             return(1)
        else:
             return(0) 

    def TPW_updateMeter(self):
        self.pollSystemData('all')
        return(None)

    def getTPW_chargeLevel(self):
 
        if self.TPWlocalAccess:
            chargeLevel = self.TPWlocal.get_charge()
        else:
            chargeLevel = self.TPWcloud.teslaExtractChargeLevel()
        chargeLevel = round(chargeLevel,2)
        logging.debug('getTPW_chargeLevel' + str(chargeLevel))
        return(chargeLevel)


    def getTPW_backoffLevel(self):
        if self.TPWlocalAccess:
            backoffLevel=self.TPWlocal.get_backup_reserve_percentage()
        else:
            backoffLevel=self.TPWcloud.teslaExtractBackoffLevel()
        logging.debug('getTPW_backoffLevel' + str(backoffLevel))
        return(round(backoffLevel,1))
    '''
    def getBackupPercentISYVar(self, node):
        logging.debug('getBackupPercentISYVar')
        return(self.isyINFO.varToISY(node, self.backoffLevel))
    '''
    

    def setTPW_backoffLevel(self, backupPercent):
        logging.debug('setTPW_backoffLevel')
        return(self.TPWcloud.teslaSetBackoffLevel(backupPercent))

    def getTPW_gridStatus(self):
        if self.TPWlocalAccess:
            statusVal = self.TPWlocal.get_grid_status()
            if statusVal.value in self.gridStatusEnum:
                key = self.gridStatusEnum[statusVal.value ]
                #logging.debug(key)
        else:
            key = self.TPWcloud.teslaExtractGridStatus()
        logging.debug('grid status '+str(self.gridstatus[key]))
        return(self.gridstatus[key])


    def getTPW_solarSupply(self):
        if self.solarInstalled:
            if self.TPWlocalAccess:
                #logging.debug(self.meters)
                solarPwr = self.solarMeter.instant_power
            else:
                solarPwr = self.TPWcloud.teslaExtractSolarSupply()
            logging.debug('getTPW_solarSupply - ' + str(solarPwr))
            return(round(solarPwr/1000,2))
            #site_live
        else:
            return(0)

    def getTPW_batterySupply(self):
        if self.TPWlocalAccess:
            batteryPwr = self.batteryMeter.instant_power
        else:
            batteryPwr = self.TPWcloud.teslaExtractBatterySupply()
        logging.debug('getTPW_batterySupply' + str(batteryPwr))
        return(round(batteryPwr/1000,2))
 


        #site_live
    def getTPW_gridSupply(self):
        if self.TPWlocalAccess:
            gridPwr = self.siteMeter.instant_power
        else:
            gridPwr = self.TPWcloud.teslaExtractGridSupply()
        logging.debug('getTPW_gridSupply'+ str(gridPwr))            
        return(round(gridPwr/1000,2))


    def getTPW_load(self):
        if self.TPWlocalAccess:
            loadPwr = self.loadMeter.instant_power
        else:
            loadPwr = self.TPWcloud.teslaExtractLoad()
        logging.debug('getTPW_load ' + str(loadPwr))
        return(round(loadPwr/1000,2))


    def getTPW_daysSolar(self):
        if self.TPWlocalAccess:
            Pwr = self.daysTotalSolar
        else:
            Pwr = self.TPWcloud.teslaExtractDaysSolar()
        logging.debug('getTPW_daysSolar ' + str(Pwr))
        return(round(Pwr/1000,2))


    def getTPW_daysConsumption(self):
        if self.TPWlocalAccess:
            Pwr = self.daysTotalConsumption
        else:
            Pwr = self.TPWcloud.teslaExtractDaysConsumption()
        logging.debug('getTPW_daysConsumption ' + str(Pwr))
        return(round(Pwr/1000,2))

    def getTPW_daysGeneration(self):  
        if self.TPWlocalAccess:
            Pwr = self.daysTotalGeneraton
        else:
            Pwr = self.TPWcloud.teslaExtractDaysGeneration()
        logging.debug('getTPW_daysGeneration ' + str(Pwr))        
        return(round(Pwr/1000,2))

    def getTPW_daysBattery(self):  
        if self.TPWlocalAccess:
            Pwr = self.daysTotalBattery
        else:
            Pwr = self.TPWcloud.teslaExtractDaysBattery()
        logging.debug('getTPW_daysBattery ' + str(Pwr))
        return(round(Pwr/1000,2))

    def getTPW_daysGrid(self):  
        if self.TPWlocalAccess:
            Pwr = self.daysTotalGrid
        else:
            Pwr = self.TPWcloud.teslaExtractDaysGrid()
        logging.debug('getTPW_daysBattery ' + str(Pwr))
        return(round(Pwr/1000,2))

    def getTPW_daysGridServicesUse(self):  
        if self.TPWlocalAccess:
            Pwr = self.daysTotalGridServices
        else:
            Pwr = self.TPWcloud.teslaExtractDaysGridServicesUse()
        logging.debug('getTPW_daysGridServicesUse ' + str(Pwr))
        return(round(Pwr/1000,2))

    def getTPW_daysGeneratorUse(self):  
        if self.generatorInstalled:
            if self.TPWlocalAccess:
                Pwr = self.daysTotalGenerator
            else:
                Pwr = self.TPWcloud.teslaExtractDaysGeneratorUse()
           
        else:
            Pwr = 0    
            logging.debug('getTPW_daysGeneratorUse ' + str(Pwr))
        return(round(Pwr/1000,2))

    def getTPW_yesterdaySolar(self):
        if self.TPWlocalAccess:
            Pwr = self.yesterdayTotalSolar
        else:
            Pwr = self.TPWcloud.teslaExtractYesteraySolar()
        logging.debug('getTPW_daysSolar ' + str(Pwr))
        return(round(Pwr/1000,2))

    def getTPW_yesterdayConsumption(self):
        if self.TPWlocalAccess:
            Pwr = self.yesterdayTotalConsumption
        else:
            Pwr = self.TPWcloud.teslaExtractYesterdayConsumption()
        logging.debug('getTPW_daysConsumption ' + str(Pwr))
        return(round(Pwr/1000,2))

    def getTPW_yesterdayGeneration(self):  
        if self.TPWlocalAccess:
            Pwr = self.yesterdayTotalGeneration
        else:
            Pwr = self.TPWcloud.teslaExtractYesterdayGeneraton()
        logging.debug('getTPW_daysGeneration ' + str(Pwr))
        return(round(Pwr/1000,2))

    def getTPW_yesterdayBattery(self):  

        if self.TPWlocalAccess:
            Pwr = self.yesterdayTotalBattery
        else:
            Pwr = self.TPWcloud.teslaExtractYesterdayBattery()
        logging.debug('getTPW_daysBattery ' + str(Pwr))
        return(round(Pwr/1000,2))

    def getTPW_yesterdayGrid(self):  

        if self.TPWlocalAccess:
            Pwr = self.yesterdayTotalGrid
        else:
            Pwr = self.TPWcloud.teslaExtractYesterdayGrid()
        logging.debug('getTPW_daysBattery ' + str(Pwr))
        return(round(Pwr/1000,2))


    def getTPW_yesterdayGridServicesUse(self):  

        if self.TPWlocalAccess:
            Pwr = self.yesterdayTotalGridServices
        else:
            Pwr = self.TPWcloud.teslaExtractYesterdayGridServiceUse()
        logging.debug('getTPW_daysGridServicesUse ' + str(Pwr))            
        return(round(Pwr/1000,2))
        #bat_history

    def getTPW_yesterdayGeneratorUse(self):  

        if self.TPWlocalAccess:
            Pwr = self.yesterdayTotalGenerator
        else:
            Pwr = self.TPWcloud.teslaExtractYesterdayGeneratorUse()
        logging.debug('getTPW_daysGeneratorUse ' + str(Pwr))
        return(round(Pwr/1000,2))
        #bat_history


    def getTPW_operationMode(self):
        if self.TPWlocalAccess:
            operationVal = self.TPWlocal.get_operation_mode()
            key = self.operationLocalEnum[operationVal.value]
        else:
            key = self.TPWcloud.teslaExtractOperationMode()
        logging.debug('getTPW_operationMode ' + str(key)) 
        return( self.ISYoperationModeEnum [key])
    
    def setTPW_operationMode(self, index):
        logging.debug('setTPW_operationMode ')  
        return(self.TPWcloud.teslaSetOperationMode(self.operationModeEnum[index]))

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
        if self.TPWlocalAccess:
            return(self.getTPW_ConnectedTesla())
        else:
            if self.TPWcloudAccess:
                return(1)
            else:
                return(0)


    def getTPW_gridServiceActive(self):
        logging.debug('getTPW_gridServiceActive ')  
        if self.TPWlocalAccess:
            res = self.TPWlocal.is_grid_services_active()   
        else:
            res = self.TPWcloud.teslaExtractGridServiceActive()
        if res:
            return(1)
        else:
            return (0)


    def getTPW_stormMode(self):
        logging.debug('getTPW_stormMode ')  
        if self.TPWcloudAccess:
            if self.TPWcloud.teslaExtractStormMode():
                return (1)
            else:
                return(0)

    def setTPW_stormMode(self, mode):
        logging.debug('getTPW_stormMode ')  
        return(self.TPWcloud.teslaSetStormMode(mode==1))

    def getTPW_touMode(self):
        logging.debug('getTPW_touMode ')  
        if self.TPWcloudAccess:
            return(self.ISYtouEnum[self.TPWcloud.teslaExtractTouMode()])        


    def getTPW_touSchedule(self):
        logging.debug('getTPW_touSchedule ')  
        if self.TPWcloudAccess:        
            return(self.TPWcloud.teslaExtractTouScheduleList())


    def setTPW_touMode(self, index):
        logging.debug('setTPW_touMode ')  
        if self.TPWcloudAccess:        
            return(self.TPWcloud.teslaSetTimeOfUseMode(self.touCloudEnum[index]))


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

    def disconnectTPW(self):
        logging.debug('disconnectTPW ')  
        if self.TPWlocalAccess:
            self.TPWlocal.close()

