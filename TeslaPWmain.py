#!/usr/bin/env python3

import sys
import time 
from TeslaInfo import tesla_info
from TeslaPWSetupNode import teslaPWSetupNode
from TeslaPWStatusNode import teslaPWStatusNode
from TeslaPWSolarNode import teslaPWSolarNode
from TeslaPWGenNode import teslaPWGenNode
from TeslaPWOauth import teslaAccess
try:
    import udi_interface
    logging = udi_interface.LOGGER
    Custom = udi_interface.Custom
    ISY = udi_interface.ISY
except ImportError:
    import logging
    logging.basicConfig(level=30)


VERSION = '0.1.2'
class TeslaPWController(udi_interface.Node):
    from  udiLib import node_queue, wait_for_node_done, mask2key

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
        self.Parameters = Custom(polyglot, 'customParams')
        self.Notices = Custom(polyglot, 'notices')
        self.my_Tesla_PW = teslaAccess(self.poly, 'energy_device_data energy_cmds open_id offline_access ')
        #self.my_Tesla_PW = TeslaCloud(self.poly, 'energy_device_data energy_cmds open_id offline_access')
        #self.my_Tesla_PW = TeslaCloud(self.poly, 'vehicle_device_data')
        self.poly.subscribe(self.poly.START, self.start, address)
        self.poly.subscribe(self.poly.LOGLEVEL, self.handleLevelChange)
        #self.poly.subscribe(self.poly.NOTICES, self.handleNotices)
        #self.poly.subscribe(self.poly.CUSTOMPARAMS, self.handleParams)
        self.poly.subscribe(self.poly.POLL, self.systemPoll)
        self.poly.subscribe(self.poly.ADDNODEDONE, self.node_queue)
        #self.poly.subscribe(self.poly.CONFIGDONE, self.check_config)
        self.poly.subscribe(self.poly.CUSTOMPARAMS, self.my_Tesla_PW.customParamsHandler)
        #self.poly.subscribe(self.poly.CUSTOMDATA, self.myNetatmo.customDataHandler)
        self.poly.subscribe(self.poly.CUSTOMNS, self.my_Tesla_PW.customNsHandler)
        self.poly.subscribe(self.poly.OAUTH, self.my_Tesla_PW.oauthHandler)
        logging.debug('self.address : ' + str(self.address))
        logging.debug('self.name :' + str(self.name))
        self.hb = 0
        self.poly.updateProfile()
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


    def start(self):
        logging.debug('start')
        self.poly.updateProfile()
        self.poly.Notices.clear()

        while not self.my_Tesla_PW.customParamsDone() or not self.my_Tesla_PW.customNsDone() : 
            logging.info('Waiting for node to initialize')
            logging.debug(' 1 2 : {} {} '.format(self.my_Tesla_PW.customParamsDone() ,self.my_Tesla_PW.customNsDone()))
            time.sleep(2)

        #self.localAccess = self.my_Tesla_PW.local_access()
        self.cloudAccess = self.my_Tesla_PW.cloud_access()
        logging.debug('Access: {} {}'.format(self.localAccess, self.cloudAccess))

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
       
        if self.cloudAccess or self.localAccess:
            self.tesla_initialize()
        else:
            self.poly.Notices['cfg'] = 'Tesla PowerWall NS needs configuration and/or LOCAL_EMAIL, LOCAL_PASSWORD, LOCAL_IP_ADDRESS'
        
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

            if self.cloudAccess:
                logging.debug('Attempting to log in via cloud auth')
                count = 1
                self.cloudAccessUp = self.my_Tesla_PW.authendicated()
                while not self.localAccessUp and count < 5:
                    self.poly.Notices['auth'] = 'Please initiate authentication'
                    time.sleep(5)
                    self.cloudAccessUp = self.my_Tesla_PW.authendicated()
                    count = count +1
                    logging.info('Waiting for cloud system access to be established')
                    self.poly.Notices['auth'] = 'Please initiate authentication'
                if not  self.cloudAccessUp:
                    logging.error('Failed to establish cloud access - ')   
                    return
                #logging.debug('local loging - accessUP {}'.format(self.localAccessUp ))
                self.poly.Notices.clear()
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
                    teslaPWStatusNode(self.poly, node_address, node_address, node_name, self.my_Tesla_PW, site_id)
                    self.wait_for_node_done()

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
            self.longPoll()
            self.nodeDefineDone = True
            self.initialized = True
            
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
    

    def heartbeat(self):
        logging.debug('heartbeat: ' + str(self.hb))
        
        if self.hb == 0:
            self.reportCmd('DON',2)
            self.hb = 1
        else:
            self.reportCmd('DOF',2)
            self.hb = 0
        
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

        for node in self.poly.nodes():
            if node.node_ready():
                node.update_PW_data()
                node.updateISYdrivers()
            else:
                logging.info('Problem polling data from Tesla system - {} may not be ready yet'.format(node.name))

    def longPoll(self):
        logging.info('Tesla Power Wall Controller longPoll')
       
        for node in self.poly.nodes():
            if node.node_ready():
                node.update_PW_data()
                node.updateISYdrivers()
            else:
                logging.info('Problem polling data from Tesla system - {} may not be ready yet'.format(node.name))
    
    def node_ready(self):
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


    def update_PW_data(self):
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