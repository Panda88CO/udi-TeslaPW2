#!/usr/bin/env python3

import sys
import time 
import traceback
from TeslaInfo import tesla_info
from TeslaLocal import tesla_local
from TeslaPWOauth import teslaPWAccess
from TeslaPWStatusNode import teslaPWStatusNode

try:
    import udi_interface
    logging = udi_interface.LOGGER
    Custom = udi_interface.Custom
    Interface = udi_interface.Interface
    ISY = udi_interface.ISY

except ImportError:
    import logging
    logging.basicConfig(level=30)


VERSION = '0.1.7'
class TeslaPWController(udi_interface.Node):
    from  udiLib import node_queue, wait_for_node_done, mask2key, heartbeat

    def __init__(self, polyglot, primary, address, name, TPW_cloud):
        super(TeslaPWController, self).__init__(polyglot, primary, address, name)

        self.poly = polyglot
        self.TPW_cloud = TPW_cloud
        logging.info('_init_ Tesla Power Wall Controller - TPW_cloud {}'.format(self.TPW_cloud))
        logging.debug('TPW_cloud {} {}'.format(self.TPW_cloud.customDataHandlerDone, self.TPW_cloud))
        self.ISYforced = False
        self.name = 'Tesla PowerWall Info'
        self.primary = primary
        self.address = address
        self.name = name
        #self.cloudAccess = False
        #self.localAccess = False
        self.config_done = False
        self.initialized = False

        self.localAccessUp = False
        self.cloudAccessUp = False
        self.customParam_done = False
        #self.Rtoken = None
        self.n_queue = []
        self.TPW = None
        self.GW = None
        self.site_id = None
        #self.Parameters = Custom(polyglot, 'customParams')
        self.customParameters = Custom(self.poly, 'customparams')
        self.Notices = Custom(self.poly, 'notices')
        self.poly.subscribe(self.poly.START, self.start, address)
        self.poly.subscribe(self.poly.LOGLEVEL, self.handleLevelChange)
        self.poly.subscribe(self.poly.NOTICES, self.handleNotices)
        self.poly.subscribe(self.poly.POLL, self.systemPoll)
        self.poly.subscribe(self.poly.ADDNODEDONE, self.node_queue)
        self.poly.subscribe(self.poly.CONFIGDONE, self.check_config)
        self.poly.subscribe(self.poly.CUSTOMPARAMS, self.customParamsHandler)
        #self.poly.subscribe(self.poly.CUSTOMDATA, self.TPW_cloud.customDataHandler)
        self.poly.subscribe(self.poly.CUSTOMNS, self.TPW_cloud.customNsHandler)
        self.poly.subscribe(self.poly.OAUTH, self.TPW_cloud.oauthHandler)
        '''
        polyglot.subscribe(polyglot.STOP, TPW.stop)
        polyglot.subscribe(polyglot.LOGLEVEL, TPW.handleLevelChange)
        polyglot.subscribe(polyglot.NOTICES, TPW.handleNotices)
        polyglot.subscribe(polyglot.POLL, TPW.systemPoll)
        polyglot.subscribe(polyglot.ADDNODEDONE, TPW.node_queue)
        polyglot.subscribe(polyglot.CONFIGDONE, TPW.check_config)
        polyglot.subscribe(polyglot.CUSTOMPARAMS, TPW.customParamsHandler)
        polyglot.subscribe(polyglot.CUSTOMDATA, TPW_cloud.TPW_cloud.customDataHandler)
        polyglot.subscribe(polyglot.CUSTOMNS, TPW_cloud.TPW_cloud.customNsHandler)
        polyglot.subscribe(polyglot.OAUTH, TPW_cloud.TPW_cloud.oauthHandler)
        '''


        logging.debug('self.address : ' + str(self.address))
        logging.debug('self.name :' + str(self.name))
        self.hb = 0
  
        self.poly.Notices.clear()
        self.nodeDefineDone = False
        self.longPollCountMissed = 0

        logging.debug('Controller init DONE')
        
       
        self.poly.addNode(self, conn_status='ST')
        self.wait_for_node_done()
        self.poly.updateProfile()
        self.node = self.poly.getNode(self.address)
        


        self.node.setDriver('ST', 1, True, True)
        logging.debug('finish Init ')

    def oauthHandler(self, token):
        # When user just authorized, pass this to your service, which will pass it to the OAuth handler
        self.TPW_cloud.oauthHandler(token)

        # Then proceed with device discovery
        self.configDoneHandler()

    def check_config(self):
        self.config_done= True

    def configDoneHandler(self):
        # We use this to discover devices, or ask to authenticate if user has not already done so
        self.poly.Notices.clear()

        # First check if user has authenticated
        try:
            self.TPW_cloud.getAccessToken()
        except ValueError as err:
            logging.warning('Access token is not yet available. Please authenticate.')
            logging.debug('Error: {}'.format(err))
            self.poly.Notices['auth'] = 'Please initiate authentication'
            return

        # If getAccessToken did raise an exception, then proceed with device discovery
        #controller.discoverDevices()


    def customParamsHandler(self, userParams):
        #logging.debug('customParamsHandler 1 : {}'.format(self.TPW_cloud._oauthTokens))
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
        logging.debug('customParamsHandler fnish ')
        self.customParam_done = True


    
    '''



    def main_module_enabled(self, node_name):
        logging.debug('main_module_enabled called {}'.format(node_name))
        if node_name in self.customParameters :           
            return(int(self.customParameters[node_name]) == 1)
        else:
            self.customParameters[node_name] = 1 #add and enable by default
            self.poly.Notices['home_id'] = 'Check config to select which home/modules should be used (1 - used, 0 - not used) - then restart'
            return(True)
    '''

    def start(self):
        site_string = ''

        logging.debug('start TPW_cloud:{}'.format(self.TPW_cloud))
        #logging.debug('start 1 : {}'.format(self.TPW_cloud._oauthTokens))
        self.poly.updateProfile()
   
        #logging.debug('start 2 : {}'.format(self.TPW_cloud._oauthTokens))
        while not self.customParam_done and not self.TPW_cloud.customNsHandlerDone and not self.TPW_cloud.customDataHandlerDone:
            logging.info('Waiting for node to initialize')
            logging.debug(' 1 2 : {} {} '.format(self.customParam_done ,self.TPW_cloud.customNsHandlerDone))
            time.sleep(5)
        logging.debug('access {} {}'.format(self.local_access_enabled, self.cloud_access_enabled))
        if self.local_access_enabled: 
            self.TPW_local = tesla_local(self.LOCAL_USER_EMAIL,self.LOCAL_USER_PASSWORD, self.LOCAL_IP_ADDRESS )
            self.TPW_local.loginLocal()
            self.GW = self.TPW_local.get_GWserial_number()
            logging.debug('local GW {}'.format(self.GW))
            site_string = self.poly.getValidAddress(str(self.GW))
            site_name = self.TPW_local.get_site_name()

        if self.cloud_access_enabled:
            logging.debug('Attempting to log in via cloud auth')

            if self.TPW_cloud.authendicated():
                self.cloudAccessUp = True
            else:
                self.cloudAccessUp =  self.TPW_cloud.try_authendication()

            while  not  self.cloudAccessUp:


                logging.info('Waiting to authenticate to complete - press authenticate button')   
                time.sleep(10)
                self.cloudAccessUp =  self.TPW_cloud.try_authendication()

            #logging.debug('local loging - accessUP {}'.format(self.localAccessUpUp ))
            self.poly.Notices.clear()     
            self.TPW_cloud.cloud_initialilze(self.region)
            PWs = self.TPW_cloud.tesla_get_products()
            logging.debug('PWs: {}'.format(PWs))
            if self.GW:
                for site in PWs:
                    logging.debug('Site Loop {}  {}'.format(site, PWs[site]))
                    if self.GW == str(PWs[site]['gateway_id']):
                        site_string = str(PWs[site]['energy_site_id'])
                        site_name = str(PWs[site]['site_name'])
                        self.site_id = site
            
            else: # No local access -                      
                for site in PWs:
                    if 'energy_site_id' in PWs[site]:
                        site_string = str(PWs[site]['energy_site_id'])
                        site_name = str(PWs[site]['site_name'])
                        self.site_id = site
                        return() # Only handle first found for now

        logging.debug(site_string)
        site_string = site_string[-14:]
        logging.debug(site_string)
        node_address =  self.poly.getValidAddress(site_string)

        site_name = PWs[site]['site_name']
        logging.debug(site_name)
        node_name = self.poly.getValidName(site_name)
        logging.debug('node_address and name: {} {}'.format(node_address, node_name))
        logging.debug(self.TPW_local)
        logging.debug(self.TPW_cloud)
        logging.debug(self.site_id )
        self.TPW = tesla_info(self.TPW_local, self.TPW_cloud, self.site_id)
        self.TPW.init_local()
        self.TPW.init_cloud()
        teslaPWStatusNode(self.poly, node_address, node_address, node_name, self.TPW)


        logging.debug('Access: {} {}'.format(self.localAccessUp, self.cloudAccessUp))

        if self.cloudAccessUp or self.localAccessUp:
            
            #logging.debug('start 3: {}'.format(self.TPW_cloud._oauthTokens))
            self.tesla_initialize()
        else:
            self.poly.Notices['cfg'] = 'Tesla PowerWall NS needs configuration and/or LOCAL_EMAIL, LOCAL_PASSWORD, LOCAL_IP_ADDRESS'
        
    #def handleNotices(self):
    #    logging.debug('handleNotices')

    def tesla_initialize(self):
        logging.debug('starting Login process')
        try:
            logging.debug('localAccess:{}, cloudAccess:{}'.format(self.localAccessUp, self.cloudAccessUp))
            
            #logging.debug('tesla_initialize 1 : {}'.format(self.TPW_cloud._oauthTokens))             

            logging.debug('Node installation complete')
            self.initialized = True
            self.longPoll()
            self.nodeDefineDone = True
            
            
        except Exception as e:
            logging.error('Exception Controller start: '+ str(e))
            logging.info('Did not connect to power wall')

        #self.TPW.systemReady = True
        logging.debug ('Controller - initialization done')

    def handleLevelChange(self, level):
        logging.info('New log level: {}'.format(level))

    def handleNotices(self, level):
        logging.info('handleNoticesl:')


    def stop(self):
        #self.removeNoticesAll()
        self.poly.Notices.clear()
        #if self.TPW:
            #self.TPW.disconnectTPW()
        self.node.setDriver('ST', 0 )
        self.poly.stop()
        logging.debug('stop - Cleaning up')
    

        
    def systemPoll(self, pollList):
        logging.info('systemPoll {}'.format(pollList))
        if self.initialized:    
            if 'longPoll' in pollList:
                self.longPoll()
            elif 'shortPoll' in pollList and 'longPoll' not in pollList:
                self.shortPoll()
        else:
            logging.info('Waiting for system/nodes to initialize')

    def shortPoll(self):
        logging.info('Tesla Power Wall Controller shortPoll')
        self.heartbeat()    
        #if self.TPW.pollSystemData('critical'):
        #should make short loop local long pool cloud 
        for node in self.poly.nodes():
            if node.node_ready():
                logging.debug('short poll node loop {} - {}'.format(node.name, node.node_ready()))
                node.update_PW_data('critical')
                node.updateISYdrivers()
            else:
                logging.info('Problem polling data from Tesla system - {} may not be ready yet'.format(node.name))

    def longPoll(self):
        logging.info('Tesla Power Wall Controller longPoll')
       
        for node in self.poly.nodes():
            logging.debug('long poll node loop {} - {}'.format(node.name, node.node_ready()))
            if node.node_ready():
                node.update_PW_data('all')
                node.updateISYdrivers()
            else:
                logging.info('Problem polling data from Tesla system - {} may not be ready yet'.format(node.name))
    
    def node_ready(self):
        logging.debug(' main node ready {} '.format(self.initialized ))
        return(self.initialized)
    

    def updateISYdrivers(self):
        logging.debug('System updateISYdrivers - ')       
        #value = self.TPW_cloud.authendicated()
        #if value == 0:
        #   self.longPollCountMissed = self.longPollCountMissed + 1
        #else:
        #   self.longPollCountMissed = 0
        #self.node.setDriver('GV2', value)
        #self.node.setDriver('GV3', self.longPollCountMissed)     
        if self.cloudAccessUp == False and self.localAccessUp == False:
            self.node.setDriver('GV4', 0)
        elif self.cloudAccessUp == True and self.localAccessUp == False:
            self.node.setDriver('GV4', 1)
        elif self.cloudAccessUp == False and self.localAccessUp == True:
            self.node.setDriver('GV4', 2)
        elif self.cloudAccessUp == True and self.localAccessUp == True:
            self.node.setDriver('GV4', 3)

        #logging.debug('CTRL Update ISY drivers : GV2  value:' + str(value) )
        #logging.debug('CTRL Update ISY drivers : GV3  value:' + str(self.longPollCountMissed) )

        #value = self.TPW.isNodeServerUp()
        #self.node.setDriver('GV2', value)
        #logging.debug('CTRL Update ISY drivers : GV2  value:' + str(value) )


    def update_PW_data(self, level):
        pass   

    def ISYupdate (self, command):
        logging.debug('ISY-update called')
        self.longPoll()


    id = 'controller'
    commands = { 'UPDATE': ISYupdate }
    drivers = [
            {'driver': 'ST', 'value':0, 'uom':25},
            {'driver': 'GV2', 'value':0, 'uom':25},
            {'driver': 'GV3', 'value':0, 'uom':55},
            {'driver': 'GV4', 'value':0, 'uom':25},
            ]

if __name__ == "__main__":
    try:
        #logging.info('Starting Tesla Power Wall Controller')
        polyglot = udi_interface.Interface([])
        polyglot.start(VERSION)
        polyglot.updateProfile()
        polyglot.setCustomParamsDoc()

        TPW_cloud = teslaPWAccess(polyglot, 'energy_device_data energy_cmds open_id offline_access')
        while not TPW_cloud.PWiniitalized:
            logging.debug('Waiting for PWservice to initialize')
            time.sleep(1)
        logging.debug('TPW_Cloud {}'.format(TPW_cloud))
        TPW =TeslaPWController(polyglot, 'controller', 'controller', 'Tesla PowerWalls', TPW_cloud)
        #polyglot.subscribe(polyglot.START, TPW.start, 'controller')

        polyglot.ready()
        polyglot.runForever()
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
    except Exception:
        logging.error(f"Error starting plugin: {traceback.format_exc()}")
        polyglot.stop()