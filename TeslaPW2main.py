#!/usr/bin/env python3

import sys
import time 
import traceback
from TeslaInfoV2 import tesla_info

from TeslaPWOauth import teslaPWAccess
from TeslaPWStatusNode import teslaPWStatusNode

try:
    import udi_interface
    logging = udi_interface.LOGGER
    Custom = udi_interface.Custom
    Interface = udi_interface.Interface


except ImportError:
    import logging
    logging.basicConfig(level=30)


VERSION = '0.2.00'
class TeslaPWController(udi_interface.Node):
    from  udiLib import node_queue, wait_for_node_done, mask2key, heartbeat, bool2ISY, PW_setDriver

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
        self.local_access_enabled = False
        self.cloud_access_enabled = False
        self.region = None
        self.LOCAL_USER_EMAIL = None
        self.LOCAL_USER_PASSWORD = None
        self.LOCAL_IP_ADDRESS = None

        self.customParam_done = False
        self.auth_executed = False
        #self.Rtoken = None
        self.n_queue = []
        self.TPW = None
        self.Gateway= None
        self.site_id = None
        
        self.customParameters = Custom(self.poly, 'customparams')

        self.Notices = Custom(self.poly, 'notices')

        self.poly.subscribe(self.poly.ADDNODEDONE, self.node_queue)


        #logging.debug('self.address : ' + str(self.address))
        #logging.debug('self.name :' + str(self.name))
        self.hb = 0

        self.poly.Notices.clear()
        self.nodeDefineDone = False
        self.longPollCountMissed = 0

        logging.debug('Controller init DONE')
        
       
        self.poly.addNode(self)
        self.wait_for_node_done()
        #self.poly.updateProfile()
        self.node = self.poly.getNode(self.address)
        logging.debug('Node info: {}'.format(self.node))
        self.node.setDriver('ST', 1, True, True)
        logging.debug('finish Init ')



    def check_config(self):
        self.nodes_in_db = self.poly.getNodesFromDb()
        self.config_done= True


    def configDoneHandler(self):
        logging.debug('configDoneHandler - config_done')
        # We use this to discover devices, or ask to authenticate if user has not already done so
        self.poly.Notices.clear()
        self.nodes_in_db = self.poly.getNodesFromDb()
        self.config_done= True
        #while not self.TPW_cloud.customNsDone() and not self.TPW_cloud.oauthHandlerCallled():
        #    logging.debug('waiting for authendication')
        #    self.poly.Notices['auth'] = 'Please initiate authentication'
        #    time.sleep(5)
            
        # First check if user has authenticated
        #try:
        #    self.TPW_cloud.getAccessToken()
        #except ValueError as err:
        #    logging.warning('Access token is not yet available. Please authenticate.')
        #    logging.debug('Error: {}'.format(err))
        #    self.poly.Notices['auth'] = 'Please initiate authentication'
        #    return

        #self.start()
        # If getAccessToken did raise an exception, then proceed with device discovery
        #controller.discoverDevices()
    
    def oauthHandler(self, token):
        self.TPW_cloud.oauthHandler(token)

    def customParamsHandler(self, userParams):
        #logging.debug('customParamsHandler 1 : {}'.format(self.TPW_cloud._oauthTokens))
        self.customParameters.load(userParams)
        logging.debug('customParamsHandler called {}'.format(userParams))
   
        oauthSettingsUpdate = {}
        #oauthSettingsUpdate['parameters'] = {}
        oauthSettingsUpdate['token_parameters'] = {}
        # Example for a boolean field

        if 'region' in userParams:
            if self.customParameters['region'] != 'Input region (NA, EU, CN)':
                self.region = str(self.customParameters['region']).strip()
                if self.region.upper() not in ['NA', 'EU', 'CN']:
                    logging.error('Unsupported region {}'.format(self.region))
                    self.poly.Notices['region'] = 'Unknown Region specified (NA = North America + Asia (-China), EU = Europe. middle East, Africa, CN = China)'
                    self.region = None
        else:
            logging.warning('No region found')
            self.customParameters['region'] = 'Input region (NA, EU, CN)'
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
        logging.debug('customParamsHandler finish ')
        self.customParam_done = True


    def start(self):
        site_string = ''
        logging.debug('start TPW_cloud:{}'.format(self.TPW_cloud))
        #logging.debug('start 1 : {}'.format(self.TPW_cloud._oauthTokens))
        self.poly.updateProfile()
        #logging.debug('start 2 : {}'.format(self.TPW_cloud._oauthTokens))
        #while not self.customParam_done or not self.TPW_cloud.customNsHandlerDone or not self.TPW_cloud.customDataHandlerDone:
        while not self.customParam_done or not self.TPW_cloud.customNsDone() or not self.config_done:
            logging.info('Waiting for node to initialize')
            logging.debug(' 1 2 3: {} {} {}'.format(self.customParam_done ,self.TPW_cloud.customNsDone(), self.config_done))
            time.sleep(1)
        logging.debug('access {} {}'.format(self.local_access_enabled, self.cloud_access_enabled))
        

        self.TPW = tesla_info(self.TPW_cloud)
    
        if self.local_access_enabled:
            count = 1
            self.localAccessUp = self.TPW.init_local(self.LOCAL_USER_EMAIL,self.LOCAL_USER_PASSWORD, self.LOCAL_IP_ADDRESS )
            while not self.localAccessUp and count <= 10:
                logging.error('local access not available - keep trying for 5 min')
                time.sleep(30)
                count += 1
                self.localAccessUp = self.TPW.init_local(self.LOCAL_USER_EMAIL,self.LOCAL_USER_PASSWORD, self.LOCAL_IP_ADDRESS )
            if count >= 10:
                self.local_access_enabled = False
                logging.error('Local access not possible - disabling it')
                self.poly.Notices['local']  = 'local access fails - disabling local access'

            #self.TPW_local.loginLocal()
            #self.Gateway= self.TPW.get_GWserial_number()
            #logging.debug('local GW {}'.format(self.GW))
            ##site_string = self.poly.getValidAddress(str(self.GW))
            #site_name = self.TPW_local.get_site_name()

        if self.cloud_access_enabled:
            logging.debug('Attempting to log in via cloud auth')
            #if not self.TPW_cloud.try_authendication():
            #    self.poly.Notices['auth'] = 'Please initiate authentication - press authenticate button'                
            #time.sleep(5)
            #while not self.TPW_cloud.oauthHandlerRun():
            #    time.sleep(1)
            #    logging.info('Waiting to oauthHandler to execute')
            while not self.TPW.cloud_authenticated():
                logging.info('Waiting to authenticate to complete - press authenticate button')
                self.poly.Notices['auth'] = 'Please initiate authentication'
                time.sleep(5)
            #if self.TPW_cloud.authenticated():
            #    self.cloudAccessUp = True
            #else:
            #    self.cloudAccessUp =  self.TPW_cloud.try_authendication()

            #while  not  self.cloudAccessUp:


            #    logging.info('Waiting to authenticate to complete - press authenticate button')   
            #    time.sleep(10)
            #    self.cloudAccessUp =  self.TPW_cloud.try_authendication()

            #logging.debug('local loging - accessUP {}'.format(self.localAccessUpUp ))
            #self.poly.Notices.clear()     
            self.cloudAccessUp = self.TPW.init_cloud(self.region)

        self.PowerWalls = self.TPW.tesla_get_products()
        self.PWs_installed = {}
        assigned_addresses =['controller'] 
        logging.debug('PowerWalls before adding nodes {}'.format(self.PowerWalls))
        for PW_site in self.PowerWalls:
            logging.debug('Adding nodes for {}'.format(PW_site))
            pw_string = self.PowerWalls[PW_site]['energy_site_id']
            site_string = pw_string[-14:]
            logging.debug(site_string)
            node_address =  self.poly.getValidAddress(site_string)
            self.PWs_installed[PW_site]= node_address
            site_name = self.PowerWalls[PW_site]['site_name']
            logging.debug(site_name)
            node_name = self.poly.getValidName(site_name)
            logging.debug('node_address and name: {} {}'.format(node_address, node_name))

            if self.cloud_access_enabled:
                self.TPW.init_cloud_data(PW_site)
            
            teslaPWStatusNode(self.poly, node_address, node_address, node_name, PW_site, self.TPW)
            assigned_addresses.append(node_address)
            if self.cloud_access_enabled:
                self.TPW.init_cloud_data(PW_site)

        logging.debug('Access: {} {}'.format(self.localAccessUp, self.cloudAccessUp))

        if self.cloudAccessUp or self.localAccessUp:            
            #logging.debug('start 3: {}'.format(self.TPW_cloud._oauthTokens))
            self.longPoll()
        else:
            self.poly.Notices['cfg'] = 'Tesla PowerWall NS needs configuration and/or LOCAL_EMAIL, LOCAL_PASSWORD, LOCAL_IP_ADDRESS'
        
        while not self.config_done:
            time.sleep(5)
        
        logging.debug('Checking for existing nodes not used anymore: {}'.format(self.nodes_in_db))
        for nde in range(0, len(self.nodes_in_db)):
            node = self.nodes_in_db[nde]
            logging.debug('Scanning db for extra nodes : {}'.format(node))
            if node['primaryNode'] not in assigned_addresses:
                logging.debug('Removing node : {} {}'.format(node['name'], node))
                self.poly.delNode(node['address'])

        self.updateISYdrivers()
        self.initialized = True
        #time.sleep(1)
    #def handleNotices(self):
    #    logging.debug('handleNotices')

    def tesla_initialize(self):
        logging.debug('starting Login process')
        try:
            logging.debug('localAccess:{}, cloudAccess:{}'.format(self.localAccess, self.cloudAccess))

            #self.TPW = tesla_info(self.my_Tesla_PW )
            #self.TPW = teslaAccess() #self.name, self.address, self.localAccess, self.cloudAccess)
            #self.localAccess = self.TPW.localAccess()
            #self.cloudAccess = self.TPW.cloudAccess()
            logging.debug('tesla_initialize 1 : {}'.format(self.my_Tesla_PW._oauthTokens))
            if self.cloudAccess:
                logging.debug('Attempting to log in via cloud auth')

                if self.my_Tesla_PW.authendicated():
                    self.cloudAccessUp = True
                else:
                    self.cloudAccessUp =  self.my_Tesla_PW.test_authendication()

                while  not  self.cloudAccessUp:
                    time.sleep(5)
                    logging.info('Waiting to authenticate to complete - press authenticate button')   
                    self.cloudAccessUp =  self.my_Tesla_PW.test_authendication()
    
                #logging.debug('local loging - accessUP {}'.format(self.localAccessUp ))
                self.poly.Notices.clear()

                logging.debug('finished login procedures' )
                logging.info('Creating Nodes')
            
                self.PWs = self.my_Tesla_PW.tesla_get_products()
                logging.debug('self.PWs {}'.format(self.PWs))
                logging.debug('tesla_initialize 2 : {}'.format(self.my_Tesla_PW._oauthTokens))
                for site_id in self.PWs:
                    string = str(self.PWs[site_id]['energy_site_id'])
                    #logging.debug(string)
                    string = string[-14:]
                    #logging.debug(string)
                    node_address =  self.poly.getValidAddress(string)
                    #logging.debug(string)
                    string = self.PWs[site_id]['site_name']
                    #logging.debug(string)
                    node_name = self.poly.getValidName(string)
                    #logging.debug(string)
                    logging.debug('tesla_initialize 3 : {}'.format(self.my_Tesla_PW._oauthTokens))
                    self.TPW = tesla_info(self.TPW_cloud)
                    teslaPWStatusNode(self.poly, node_address, node_address, node_name, self.TPW , site_id)
                    logging.debug('tesla_initialize 4 : {}'.format(self.my_Tesla_PW._oauthTokens))
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

    def handleNotices(self, level):
        logging.info('handleNotices:')


    def addNodeDoneHandler(self, node):
        pass
        # We will automatically query the device after discovery
        #controller.addNodeDoneHandler(node)


    def stop(self):
        #self.removeNoticesAll()

        self.poly.Notices.clear()
        try:
            if self.TPW:
                self.TPW.disconnectTPW()
        except Exception as e:
            logging.debug('Local logout failed {}'.format(e))
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
        for site_id in self.PowerWalls:
            self.TPW.pollSystemData(site_id, 'critical')
        for node in self.poly.nodes():
            if node.node_ready():
                logging.debug('short poll node loop {} - {}'.format(node.name, node.node_ready()))
                #node.update_PW_data('all')
                node.updateISYdrivers()
            else:
                logging.info('Problem polling data from Tesla system - {} may not be ready yet'.format(node.name))

    def longPoll(self):
        logging.info('Tesla Power Wall Controller longPoll')
        for site_id in self.PowerWalls:
            if not self.TPW.pollSystemData(site_id, 'all'):
                self.longPollCountMissed += 1
            else:
                self.longPollCountMissed = 0
        for node in self.poly.nodes():
            logging.debug('long poll node loop {} - {}'.format(node.name, node.node_ready()))
            if node.node_ready():
                #node.update_PW_data('all')
                node.updateISYdrivers()
            else:
                logging.info('Problem polling data from Tesla system - {} may not be ready yet'.format(node.name))
    
    def node_ready(self):
        logging.debug(' main node ready {} '.format(self.initialized ))
        return(self.initialized)
    

    def updateISYdrivers(self):
        logging.debug('System updateISYdrivers - ')       
        #value = self.TPW_cloud.authenticated()
        #if value == 0:
        #   self.longPollCountMissed = self.longPollCountMissed + 1
        #else:
        #   self.longPollCountMissed = 0
        self.PW_setDriver('ST', self.bool2ISY( self.cloudAccessUp  or self.localAccessUp ))
        self.PW_setDriver('GV2', self.bool2ISY(self.TPW.getTPW_onLine()))
        self.PW_setDriver('GV3', self.longPollCountMissed)
        #self.node.setDriver('GV3', self.longPollCountMissed)     
        if self.cloud_access_enabled == False and self.local_access_enabled == False:
            self.PW_setDriver('GV4', 0)
        elif self.cloud_access_enabled == True and self.local_access_enabled == False:
            self.PW_setDriver('GV4', 1)
        elif self.cloud_access_enabled == False and self.local_access_enabled == True:
            self.PW_setDriver('GV4', 2)
        elif self.cloud_access_enabled == True and self.local_access_enabled == True:
            self.PW_setDriver('GV4', 3)

        #logging.debug('CTRL Update ISY drivers : GV2  value:' + str(value) )
        #logging.debug('CTRL Update ISY drivers : GV3  value:' + str(self.longPollCountMissed) )

        #value = self.TPW.isNodeServerUp()
        #self.node.setDriver('GV2', value)
        #logging.debug('CTRL Update ISY drivers : GV2  value:' + str(value) )


    def update_PW_data(self, site_id, level):
        pass   

    def ISYupdate (self, command):
        logging.debug('ISY-update called')
        self.longPoll()


    id = 'controller'
    commands = { 'UPDATE': ISYupdate }
    drivers = [
            {'driver': 'ST', 'value':0, 'uom':25},
            {'driver': 'GV2', 'value':0, 'uom':25},
            {'driver': 'GV3', 'value':99, 'uom':25},
            {'driver': 'GV4', 'value':0, 'uom':25},
            ]

if __name__ == "__main__":
    try:
        #logging.info('Starting Tesla Power Wall Controller')
        polyglot = udi_interface.Interface([])
        polyglot.start(VERSION)
        #polyglot.updateProfile()
        polyglot.setCustomParamsDoc()

        TPW_cloud = teslaPWAccess(polyglot, 'energy_device_data energy_cmds open_id offline_access')

        logging.debug('TPW_Cloud {}'.format(TPW_cloud))
        TPW =TeslaPWController(polyglot, 'controller', 'controller', 'Tesla PowerWalls', TPW_cloud)
        #polyglot.addNode(TPW)
        
        logging.debug('before subscribe')
        polyglot.subscribe(polyglot.STOP, TPW.stop)
        polyglot.subscribe(polyglot.CUSTOMPARAMS, TPW.customParamsHandler)
        polyglot.subscribe(polyglot.CUSTOMDATA, None) # ytService.customDataHandler)
        polyglot.subscribe(polyglot.CONFIGDONE, TPW.configDoneHandler)
        #polyglot.subscribe(polyglot.ADDNODEDONE, TPW.node_queue)        
        polyglot.subscribe(polyglot.LOGLEVEL, TPW.handleLevelChange)
        polyglot.subscribe(polyglot.NOTICES, TPW.handleNotices)
        polyglot.subscribe(polyglot.POLL, TPW.systemPoll)
        polyglot.subscribe(polyglot.START, TPW.start, 'controller')
        logging.debug('Calling start')
        polyglot.subscribe(polyglot.CUSTOMNS, TPW_cloud.customNsHandler)
        polyglot.subscribe(polyglot.OAUTH, TPW_cloud.oauthHandler)
        logging.debug('after subscribe')
        polyglot.ready()
        polyglot.runForever()
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
    except Exception:
        logging.error(f"Error starting plugin: {traceback.format_exc()}")
        polyglot.stop()