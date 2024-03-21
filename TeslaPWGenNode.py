#!/usr/bin/env python3

try:
    import udi_interface
    logging = udi_interface.LOGGER
    Custom = udi_interface.Custom
except ImportError:
    import logging
    logging.basicConfig(level=30)
import time
               
class teslaPWGenNode(udi_interface.Node):
    from  udiYolinkLib import node_queue, wait_for_node_done, mask2key

    def __init__(self, polyglot, primary, address, name, TPW, site_id):
        super(teslaPWGenNode, self).__init__(polyglot, primary, address, name)
        logging.info('_init_ Tesla Power Wall Generator Status Node')
        self.ISYforced = False
        self.TPW = TPW
        self.poly = polyglot
        self.site_id = site_id
        self.n_queue = []
        self.poly.subscribe(self.poly.ADDNODEDONE, self.node_queue)

        self.poly.ready()
        self.poly.addNode(self, conn_status = None, rename = True)
        self.wait_for_node_done()
        self.node = self.poly.getNode(address)
        
    def start(self):                
        logging.debug('Start Tesla Power Wall Generator Node')  
        while not self.TPW.systemReady:
            time.sleep(1)
        self.updateISYdrivers('all')

    def stop(self):
        logging.debug('stop - Cleaning up')
    
    def updateISYdrivers(self, level):
        if self.TPW.systemReady:
            logging.debug('SolarNode updateISYdrivers')
            self.node.setDriver('GV1', self.TPW.getTPW_daysGeneratorUse(self.site_id))
            self.node.setDriver('GV2', self.TPW.getTPW_yesterdayGeneratorUse(self.site_id))
        else:
            logging.debug('System not ready yet')

    def ISYupdate (self, command):
        logging.debug('ISY-update called')
        if self.TPW.pollSystemData('all'):
            self.updateISYdrivers('all')
 
    def update_PW_data(self, type):
        pass 

    id = 'pwgenerator'
    commands = { 'UPDATE': ISYupdate, 
                }

    drivers = [
            {'driver': 'GV1', 'value': 0, 'uom': 33},  #generator today
            {'driver': 'GV2', 'value': 0, 'uom': 33},  #generator yesterday
            ]


