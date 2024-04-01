#!/usr/bin/env python3

import sys
import time 
from TeslaInfo import tesla_info
from TeslaLocal import tesla_local

#from TeslaPWSetupNode import teslaPWSetupNode
from TeslaPWStatusNode import teslaPWStatusNode
#from TeslaPWSolarNode import teslaPWSolarNode
#from TeslaPWGenNode import teslaPWGenNode
from TeslaPWOauth import teslaAccess
try:
    import udi_interface
    logging = udi_interface.LOGGER
    Custom = udi_interface.Custom
    ISY = udi_interface.ISY
except ImportError:
    import logging
    logging.basicConfig(level=30)


VERSION = '0.1.5'
class TeslaPWController(udi_interface.Node):
    from  udiLib import node_queue, wait_for_node_done, mask2key, heartbeat

    def __init__(self, polyglot, primary, address, name):
        super(TeslaPWController, self).__init__(polyglot, primary, address, name)
        self.poly = polyglot

        logging.info('_init_ Tesla Power Wall Controller')
        self.ISYforced = False
        self.name = 'Tesla PowerWall Info'
        self.primary = primary
        self.address = address
        self.name = name
        self.cloudAccess = False
        self.localAccess = False
        self.initialized = False
        self.localAccessUp = False
        self.cloudAccessUp = False
        #self.Rtoken = None
        self.n_queue = []
        self.TPW = None
        self.GW = None
        self.Parameters = Custom(polyglot, 'customParams')
        self.Notices = Custom(polyglot, 'notices')
        self.my_Tesla_PW = teslaAccess(self.poly, 'energy_device_data energy_cmds open_id offline_access')
        #self.my_Tesla_PW = TeslaCloud(self.poly, 'energy_device_data energy_cmds open_id offline_access')
        #self.my_Tesla_PW = TeslaCloud(self.poly, 'vehicle_device_data')
        self.poly.subscribe(self.poly.START, self.start, address)
        self.poly.subscribe(self.poly.LOGLEVEL, self.handleLevelChange)
        #self.poly.subscribe(self.poly.NOTICES, self.handleNotices)
        #self.poly.subscribe(self.poly.CUSTOMPARAMS, self.handleParams)
        self.poly.subscribe(self.poly.POLL, self.systemPoll)
        self.poly.subscribe(self.poly.ADDNODEDONE, self.node_queue)
        #self.poly.subscribe(self.poly.CONFIGDONE, self.check_config)
        self.poly.subscribe(self.poly.CUSTOMPARAMS, self.customParamsHandler)
        #self.poly.subscribe(self.poly.CUSTOMDATA, self.myNetatmo.customDataHandler)
        self.poly.subscribe(self.poly.CUSTOMNS, self.my_Tesla_PW.customNsHandler)
        self.poly.subscribe(self.poly.OAUTH, self.my_Tesla_PW.oauthHandler)
        logging.debug('self.address : ' + str(self.address))
        logging.debug('self.name :' + str(self.name))
        self.hb = 0
  
        self.poly.Notices.clear()
        self.nodeDefineDone = False
        self.longPollCountMissed = 0

        logging.debug('Controller init DONE')
        
        self.poly.ready()
        self.poly.addNode(self, conn_status='ST')
        self.wait_for_node_done()
        self.poly.updateProfile()
        self.node = self.poly.getNode(self.address)



        self.node.setDriver('ST', 1, True, True)
        logging.debug('finish Init ')



    def customParamsHandler(self, userParams):
        logging.debug('customParamsHandler 1 : {}'.format(self.my_Tesla_PW._oauthTokens))
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
      
      
    def start(self):
        logging.debug('start')
        logging.debug('start 1 : {}'.format(self.my_Tesla_PW._oauthTokens))
        self.poly.updateProfile()
   

        logging.debug('start 2 : {}'.format(self.my_Tesla_PW._oauthTokens))
        while not self.my_Tesla_PW.customParamsDone() or not self.my_Tesla_PW.customNsDone() : 
            logging.info('Waiting for node to initialize')
            logging.debug(' 1 2 : {} {} '.format(self.my_Tesla_PW.customParamsDone() ,self.my_Tesla_PW.customNsDone()))
            time.sleep(2)

        if self.local_access_enabled: 
            self.TPW_local = tesla_local(self.LOCAL_USER_EMAIL,self.LOCAL_USER_PASSWORD, self.LOCAL_IP_ADDRESS )
            self.GW = self, self.TPW_local.get_GWserial_number()
        
        if self.cloud_access_enabled:
            if self.GW:
                
            
            
            self.cloudAccess = self.my_Tesla_PW.cloud_access()

        logging.debug('Access: {} {}'.format(self.localAccess, self.cloudAccess))

        '''
        if self.cloudAccess:
            no_message = True
            while not self.my_Tesla_PW.authendicated():
                
                logging.info('Waiting for authendication')
                if no_message:
                    self.poly.Notices['auth'] = 'Please initiate authentication'
                    no_message = False
                time.sleep(5)
            self.poly.Notices.clear()
        #self.TPW = tesla_info(self.my_Tesla_PW)
        #self.poly.setCustomParamsDoc()
        # Wait for things to initialize....
        #self.check_config()
        #while not self.initialized:
        #    time.sleep(1)
        '''
        if self.cloudAccess or self.localAccess:
            
            logging.debug('start 3: {}'.format(self.my_Tesla_PW._oauthTokens))
            self.tesla_initialize()
        else:
            self.poly.Notices['cfg'] = 'Tesla PowerWall NS needs configuration and/or LOCAL_EMAIL, LOCAL_PASSWORD, LOCAL_IP_ADDRESS'
        
    #def handleNotices(self):
    #    logging.debug('handleNotices')

    def tesla_initialize(self):
        logging.debug('starting Login process')
        try:
            logging.debug('localAccess:{}, cloudAccess:{}'.format(self.localAccess, self.cloudAccess))
            
            logging.debug('tesla_initialize 1 : {}'.format(self.my_Tesla_PW._oauthTokens))
            #self.TPW = tesla_info(self.my_Tesla_PW )
            #self.TPW = teslaAccess() #self.name, self.address, self.localAccess, self.cloudAccess)
            #self.localAccess = self.TPW.localAccess()
            #self.cloudAccess = self.TPW.cloudAccess()

            if self.cloudAccess:
                logging.debug('Attempting to log in via cloud auth')
                count = 1
                logging.debug('tesla_initialize 1 : {}'.format(self.my_Tesla_PW._oauthTokens))
                if self.my_Tesla_PW.authendicated():
                    self.cloudAccessUp = True
                while not self.cloudAccessUp and count < 5:
                    self.poly.Notices['auth'] = 'Please initiate authentication - press Authenticate button'
                    time.sleep(5)
                    if self.my_Tesla_PW.authendicated():
                        self.cloudAccessUp = True
                    count = count +1
                    logging.info('Waiting for cloud system access to be established')
                if not  self.cloudAccessUp:
                    logging.error('Failed to establish cloud access - ')   
                    if not self.localAccess:
                        return
                #logging.debug('local loging - accessUP {}'.format(self.localAccessUp ))
                self.poly.Notices.clear()
                logging.debug('tesla_initialize 1 : {}'.format(self.my_Tesla_PW._oauthTokens))
                logging.debug('finished login procedures' )
                logging.info('Creating Nodes')
            
                self.PWs = self.my_Tesla_PW.tesla_get_products()
                logging.debug('self.PWs {}'.format(self.PWs))

                for site_id in self.PWs:
                    string = str(self.PWs[site_id]['energy_site_id'])
                    logging.debug(string)
                    string = string[-14:]
                    logging.debug(string)
                    node_address =  self.poly.getValidAddress(string)
                    logging.debug(string)
                    string = self.PWs[site_id]['site_name']
                    logging.debug(string)
                    node_name = self.poly.getValidName(string)
                    logging.debug(string)
                    self.TPW = tesla_info(self.my_TeslaPW, self.site_id)
                    teslaPWStatusNode(self.poly, node_address, node_address, node_name, self.TPW , site_id)
                    #self.wait_for_node_done()

            else:
                logging.info('Cloud Acces not enabled')
            '''
            if self.localAccess:
                logging.debug('Attempting to log in via local auth')
                try:
                    self.poly.Notices['localPW'] = 'Tesla PowerWall may need to be turned OFF and back ON to allow loacal access'
                    #self.localAccessUp  = self.TPW.loginLocal(local_email, local_password, local_ip)
                    self.localAccessUp  = self.TPW.loginLocal()
                    count = 1
                    while not self.localAccessUp and count < 5:
                        time.sleep(1)
                        self.localAccessUp  = self.TPW.loginLocal()
                        count = count +1
                        logging.info('Waiting for local system access to be established')
                    if not  self.localAccessUp:
                        logging.error('Failed to establish local access - check email, password and IP address')   
                        return
                    logging.debug('local loging - accessUP {}'.format(self.localAccessUp ))

                except:
                    logging.error('local authenticated failed.')
                    self.localAccess = False
            '''
                
 
            
            '''
            node addresses:
               setup node:            pwsetup 'Control Parameters'
               main status node:      pwstatus 'Power Wall Status'
               generator status node: genstatus 'Generator Status'
               
            

            if not self.poly.getNode('pwstatus'):
                node = teslaPWNode(self.poly, self.address, 'pwstatus', 'Power Wall Status', self.TPW, site_id)
                self.poly.addNode(node)
                self.wait_for_node_done()

            if self.TPW.solarInstalled:
                if not self.poly.getNode('solarstatus'):
                    node = teslaPWSolarNode(self.poly, self.address, 'solarstatus', 'Solar Status', self.TPW)
                    self.poly.addNode(node)
                    self.wait_for_node_done()
            else:
                temp = self.poly.getNode('solarstatus')
                if temp:
                    self.poly.delNode(temp)


            if self.TPW.generatorInstalled:
                if not self.poly.getNode('genstatus'):
                    node = teslaPWGenNode(self.poly, self.address, 'genstatus', 'Generator Status', self.TPW)
                    self.poly.addNode(node)
                    self.wait_for_node_done()
            else:
                temp = self.poly.getNode('genstatus')
                if temp:
                    self.poly.delNode(temp)
        
            if self.cloudAccess:
                if not self.poly.getNode('pwsetup'):
                    node = teslaPWSetupNode(self.poly, self.address, 'pwsetup', 'Control Parameters', self.TPW)
                    self.poly.addNode(node)
                    self.wait_for_node_done()
            else:
                self.poly.delNode('pwsetup')
            '''
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
            elif 'shortPoll' in pollList:
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
        #value = self.my_Tesla_PW.authendicated()
        #if value == 0:
        #   self.longPollCountMissed = self.longPollCountMissed + 1
        #else:
        #   self.longPollCountMissed = 0
        #self.node.setDriver('GV2', value)
        #self.node.setDriver('GV3', self.longPollCountMissed)     
        if self.cloudAccess == False and self.localAccess == False:
            self.node.setDriver('GV4', 0)
        elif self.cloudAccess == True and self.localAccess == False:
            self.node.setDriver('GV4', 1)
        elif self.cloudAccess == False and self.localAccess == True:
            self.node.setDriver('GV4', 2)
        elif self.cloudAccess == True and self.localAccess == True:
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
        TeslaPWController(polyglot, 'controller', 'controller', 'TeslaPowerWalls')
        polyglot.runForever()
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)