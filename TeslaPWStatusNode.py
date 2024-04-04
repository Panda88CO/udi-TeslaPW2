#!/usr/bin/env python3

import time

try:
    import udi_interface
    logging = udi_interface.LOGGER
    Custom = udi_interface.Custom
except ImportError:
    import logging
    logging.basicConfig(level=30)

from TeslaInfo import tesla_info
from TeslaPWSetupNode import teslaPWSetupNode
from TeslaPWSolarNode import teslaPWSolarNode
from TeslaPWGenNode import teslaPWGenNode
from TeslaPWHistoryNode import teslaPWHistoryNode


class teslaPWStatusNode(udi_interface.Node):
    from  udiLib import node_queue, wait_for_node_done, mask2key

    def __init__(self, polyglot, primary, address, name, TPW):
        #super(teslaPWStatusNode, self).__init__(polyglot, primary, address, name)
        logging.info('_init_ Tesla Power Wall Status Node')
        self.poly = polyglot
        self.ISYforced = False
        self.TPW = TPW
        self.node_ok = False
        self.address = address
        self.primary = primary
        self.name = name
        self.n_queue = []
        self.poly.subscribe(self.poly.ADDNODEDONE, self.node_queue)
        self.poly.subscribe(self.poly.START, self.start, address)

        self.poly.ready()
        self.poly.addNode(self)
        self.wait_for_node_done()
        self.node = self.poly.getNode(address)
        #self.TPW = tesla_info(self.my_TeslaPW, self.site_id)
        #self.TPW.tesla_get_site_info(self.site_id)
        #self.TPW.tesla_get_live_status(self.site_id)
        
        #polyglot.subscribe(polyglot.START, self.start, address)
        
    def start(self):   
        logging.debug('Start Tesla Power Wall Status Node')
        #self.TPW = tesla_info(self.my_TeslaPW, self.site_id)
        logging.info('Adding power wall sub-nodes')

        sub_adr = self.primary[-8:]
        #if self.TPW.cloud_access_enabled():
        self.TPW.teslaInitializeData()
        teslaPWSetupNode(self.poly, self.primary, 'setup_'+sub_adr, 'Setup PW Parameters', self.TPW)
        if self.TPW.solarInstalled:
            teslaPWSolarNode(self.poly, self.primary, 'solar_'+sub_adr, 'Solar Status', self.TPW)
        if self.TPW.generatorInstalled:
            teslaPWGenNode(self.poly, self.primary, 'extpwr'+sub_adr, 'Generator Status', self.TPW)
        teslaPWHistoryNode(self.poly, self.primary, 'hist_'+sub_adr, 'History', self.TPW)


        self.TPW.teslaInitializeData()
        self.updateISYdrivers()
        self.node_ok = True

    def stop(self):
        logging.debug('stop - Cleaning up')
    
    def node_ready(self):
        return(self.node_ok)


 
    
    def updateISYdrivers(self):


        logging.debug('StatusNode updateISYdrivers')
        #tmp = self.TPW.getTPW_backup_time_remaining()
        #logging.debug('GV0: {}'.format(tmp))
        #self.node.setDriver('GV0', round(tmp,2))
        if self.TPW.getTPW_energy_remaining():
            logging.debug(('GV0: Battery Energy remiaining: {}'.format(self.TPW.getTPW_energy_remaining())))
            self.node.setDriver('GV0', self.TPW.getTPW_energy_remaining())
        else:
             self.node.setDriver('GV1', 99, True, True, 25)
        logging.debug('GV1: '+ str(self.TPW.getTPW_chargeLevel()))
        self.node.setDriver('GV1', self.TPW.getTPW_chargeLevel())
        logging.debug('GV2: '+ str(self.TPW.getTPW_operationMode()))
        self.node.setDriver('GV2', self.TPW.getTPW_operationMode())
        logging.debug('GV3: '+ str(self.TPW.getTPW_gridStatus()))
        self.node.setDriver('GV3', self.TPW.getTPW_gridStatus())
        logging.debug('GV4: '+ str(self.TPW.getTPW_onLine()))
        self.node.setDriver('GV4', self.TPW.getTPW_onLine())
        logging.debug('GV5: '+ str(self.TPW.getTPW_gridServiceActive()))
        self.node.setDriver('GV5', self.TPW.getTPW_gridServiceActive())
        logging.debug('GV6: '+ str(self.TPW.getTPW_chargeLevel()))
        self.node.setDriver('GV6', self.TPW.getTPW_chargeLevel())
        logging.debug('GV9: '+ str(self.TPW.getTPW_gridSupply()))
        self.node.setDriver('GV9', self.TPW.getTPW_gridSupply())
        logging.debug('GV12: '+ str(self.TPW.getTPW_load()))
        self.node.setDriver('GV12', self.TPW.getTPW_load())
        
        self.node.setDriver('GV7', self.TPW.getTPW_daysBattery())
        #self.node.setDriver('GV8', self.TPW.getTPW_yesterdayBattery())
        self.node.setDriver('GV10', self.TPW.getTPW_daysGrid())
        #self.node.setDriver('GV11', self.TPW.getTPW_yesterdayGrid())
        self.node.setDriver('GV13', self.TPW.getTPW_daysConsumption())
        #self.node.setDriver('GV14', self.TPW.getTPW_yesterdayConsumption())
        self.node.setDriver('GV15', self.TPW.getTPW_daysGeneration())
        #self.node.setDriver('GV16', self.TPW.getTPW_yesterdayGeneration())
        self.node.setDriver('GV17', self.TPW.getTPW_daysGridServicesUse())
        #self.node.setDriver('GV18', self.TPW.getTPW_yesterdayGridServicesUse())
        self.node.setDriver('GV17', self.TPW.getTPW_daysSolar())
        #self.node.setDriver('GV20', self.TPW.getTPW_yesterdaySolar())



    def update_PW_data(self, level):
        self.TPW.pollSystemData(level) 


    def ISYupdate (self, command):
        logging.debug('ISY-update called')
        self.update_PW_data('all')
        self.updateISYdrivers()

 

    id = 'pwstatus'
    commands = { 'UPDATE': ISYupdate, 
                }


    drivers = [
            {'driver': 'GV0', 'value': -1, 'uom': 33},  #battery level
            {'driver': 'GV1', 'value': 0, 'uom': 51},  #battery level
            {'driver': 'GV2', 'value': 0, 'uom': 25},  #mode
            {'driver': 'GV3', 'value': 0, 'uom': 25},  #grid status
            {'driver': 'GV4', 'value': 0, 'uom': 25},  #on/off line
            {'driver': 'GV5', 'value': 0, 'uom': 25},  #grid services
            {'driver': 'GV6', 'value': 0, 'uom': 33},  #battery supply
            {'driver': 'GV7', 'value': 0, 'uom': 33},  #battery today
            #{'driver': 'GV8', 'value': 0, 'uom': 33},  #battery yesterday
            {'driver': 'GV9', 'value': 0, 'uom': 33},  #grid supply
            {'driver': 'GV10', 'value': 0, 'uom': 33}, #grid today
            #{'driver': 'GV11', 'value': 0, 'uom': 33}, #grid yesterday
            {'driver': 'GV12', 'value': 0, 'uom': 33}, #load
            {'driver': 'GV13', 'value': 0, 'uom': 33}, #consumption today
            #{'driver': 'GV14', 'value': 0, 'uom': 33}, #consumption yesterday
            {'driver': 'GV15', 'value': 0, 'uom': 33}, #generation today
            #{'driver': 'GV16', 'value': 0, 'uom': 33}, #generation yesterday
            {'driver': 'GV17', 'value': 0, 'uom': 33}, #grid service today
            #{'driver': 'GV18', 'value': 0, 'uom': 33}, #grid service yesterday
            {'driver': 'GV19', 'value': 0, 'uom': 33}, #Solar today
            #{'driver': 'GV20', 'value': 0, 'uom': 33}, #Solar yesterday
            #{'driver': 'GV20', 'value': 0, 'uom': 33}, #Solar yesterday
            #{'driver': 'GV21', 'value': 0, 'uom': 103}, #Current buy rate
            #{'driver': 'GV22', 'value': 0, 'uom': 103}, #Current sell rate
            #{'driver': 'GV23', 'value': 99, 'uom': 25}, #Peak/Partial/offpeak
            #{'driver': 'GV24', 'value': 99, 'uom': 25}, #Summer/Winter
           
           
            ]


