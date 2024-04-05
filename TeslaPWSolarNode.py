#!/usr/bin/env python3

import time
try:
    import udi_interface
    logging = udi_interface.LOGGER
    Custom = udi_interface.Custom
except ImportError:
    import logging
    logging.basicConfig(level=30)
               
class teslaPWSolarNode(udi_interface.Node):
    from  udiLib import node_queue, wait_for_node_done, mask2key, bool2ISY

    def __init__(self, polyglot, primary, address, name, TPW):
        super(teslaPWSolarNode, self).__init__(polyglot, primary, address, name)
        logging.info('_init_ Tesla Power Wall Status Node')
        self.ISYforced = False
        self.TPW = TPW
        self.poly = polyglot
        self.name = name
        self.node_ok = False
        self.n_queue = []
        self.poly.subscribe(self.poly.ADDNODEDONE, self.node_queue)
        self.poly.subscribe(self.poly.START, self.start, address)
        self.poly.ready()
        self.poly.addNode(self, conn_status = None, rename = True)
        self.wait_for_node_done()
        self.node = self.poly.getNode(address)
        
    def start(self):                
        logging.debug('Start Tesla Power Wall Solar Node')  
        #while not self.TPW.systemReady:
        #    time.sleep(1)
        self.updateISYdrivers()
        self.node_ok = True

    def stop(self):
        logging.debug('stop - Cleaning up')
    
    def updateISYdrivers(self):
        logging.debug('SolarNode updateISYdrivers')
        self.node.setDriver('GV1', self.TPW.getTPW_solarSupply())
        self.node.setDriver('GV2', self.TPW.getTPW_daysSolar())
        self.node.setDriver('GV3', self.TPW.getTPW_yesterdaySolar())

    def node_ready(self):
        return(self.node_ok)

    def update_PW_data(self, level):
        pass 

    def ISYupdate (self, command):
        logging.debug('ISY-update called')
        #if self.TPW.pollSystemData():
        self.updateISYdrivers()

 

    id = 'pwsolar'
    commands = { 'UPDATE': ISYupdate, 
                }

    drivers = [
            {'driver': 'GV1', 'value': 0, 'uom': 33},  #Current solar supply
            {'driver': 'GV2', 'value': 0, 'uom': 33},  #solar power today
            {'driver': 'GV3', 'value': 0, 'uom': 33},  #solar power yesterday
            ]


