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


class teslaPWStatusNode(udi_interface.Node):
    from  udiYolinkLib import node_queue, wait_for_node_done, mask2key

    def __init__(self, polyglot, primary, address, name, TPW, site_id):
        super(teslaPWStatusNode, self).__init__(polyglot, primary, address, name)
        logging.info('_init_ Tesla Power Wall Status Node')
        self.poly = polyglot
        self.ISYforced = False
        self.TPW = TPW
        self.site_id = site_id
        self.primary = primary
        self.address = address 
        self.poly.ready()
        self.poly.addNode(self, conn_status = None, rename = True)
        self.wait_for_node_done()
        self.node = self.poly.getNode(address)
            
        #polyglot.subscribe(polyglot.START, self.start, address)
        
    def start(self):       
        logging.debug('Start Tesla Power Wall Status Node')  
        logging.info('Adding power wall sub-nodes')
        sub_adr = self.primary[-8:]

        if self.cloudAccess:
            teslaPWSetupNode(self.poly, self.primary, 'setup_'+sub_adr, 'Setup PW Parameters', self.TPW, self.site_id)
            teslaPWSolarNode(self.poly, self.primary, 'solar_'+sub_adr, 'Solar Status', self.TPW, self.site_id)
            teslaPWGenNode(self.poly, self.primary, 'extpwr'+sub_adr, 'Generator Status', self.TPW, self.site_id)
        
        while not self.TPW.systemReady:
            time.sleep(1)
        self.updateISYdrivers('all')

    def stop(self):
        logging.debug('stop - Cleaning up')
    



    def season2ISY(self, season):
        logging.debug('season2ISY {}'.format(season))
        if season.upper() == 'WINTER':
            return(0)
        elif season.upper() == 'SUMMER':
            return(1)
        elif season != None:
            return(2)
        else:
            return (99)
        

    def period2ISY(self, period):
        logging.debug('period2ISY {}'.format(period))
        if period.upper() == 'OFF_PEAK':
            return(0)
        elif period.upper() == 'PARTIAL_PEAK':
            return(1)
        elif period.upper() == 'PEAK':
            return(2)
        else:
            return (99) 

    def updateISYdrivers(self, level):
        if self.TPW.systemReady:

            logging.debug('StatusNode updateISYdrivers')
            tmp = self.TPW.getTPW_backup_time_remaining()
            logging.debug('GV0: {}'.format(tmp))
            self.node.setDriver('GV0', round(tmp,2))
            logging.debug('GV1: '+ str(self.TPW.getTPW_chargeLevel(self.site_id)))
            self.node.setDriver('GV1', self.TPW.getTPW_chargeLevel(self.site_id))
            logging.debug('GV2: '+ str(self.TPW.getTPW_operationMode(self.site_id)))
            self.node.setDriver('GV2', self.TPW.getTPW_operationMode(self.site_id))
            logging.debug('GV3: '+ str(self.TPW.getTPW_gridStatus(self.site_id)))
            self.node.setDriver('GV3', self.TPW.getTPW_gridStatus(self.site_id))
            logging.debug('GV4: '+ str(self.TPW.getTPW_onLine(self.site_id)))
            self.node.setDriver('GV4', self.TPW.getTPW_onLine(self.site_id))
            logging.debug('GV5: '+ str(self.TPW.getTPW_gridServiceActive(self.site_id)))
            self.node.setDriver('GV5', self.TPW.getTPW_gridServiceActive(self.site_id))
            logging.debug('GV6: '+ str(self.TPW.getTPW_chargeLevel(self.site_id)))
            self.node.setDriver('GV6', self.TPW.getTPW_chargeLevel(self.site_id))
            logging.debug('GV9: '+ str(self.TPW.getTPW_gridSupply(self.site_id)))
            self.node.setDriver('GV9', self.TPW.getTPW_gridSupply(self.site_id))
            logging.debug('GV12: '+ str(self.TPW.getTPW_load(self.site_id)))
            self.node.setDriver('GV12', self.TPW.getTPW_load(self.site_id))
            
            if level == 'all':
                self.node.setDriver('GV7', self.TPW.getTPW_daysBattery(self.site_id))
                self.node.setDriver('GV8', self.TPW.getTPW_yesterdayBattery(self.site_id))
                self.node.setDriver('GV10', self.TPW.getTPW_daysGrid(self.site_id))
                self.node.setDriver('GV11', self.TPW.getTPW_yesterdayGrid(self.site_id))
                self.node.setDriver('GV13', self.TPW.getTPW_daysConsumption(self.site_id))
                self.node.setDriver('GV14', self.TPW.getTPW_yesterdayConsumption(self.site_id))
                self.node.setDriver('GV15', self.TPW.getTPW_daysGeneration(self.site_id))
                self.node.setDriver('GV16', self.TPW.getTPW_yesterdayGeneration(self.site_id))
                self.node.setDriver('GV17', self.TPW.getTPW_daysGridServicesUse(self.site_id))
                self.node.setDriver('GV18', self.TPW.getTPW_yesterdayGridServicesUse(self.site_id))
                self.node.setDriver('GV17', self.TPW.getTPW_daysSolar(self.site_id))
                self.node.setDriver('GV20', self.TPW.getTPW_yesterdaySolar(self.site_id))

        else:
            logging.debug('System not ready yet')


    def ISYupdate (self, command):
        logging.debug('ISY-update called')
        if self.TPW.pollSystemData('all'):
            self.updateISYdrivers('all')

 

    id = 'pwstatus'
    commands = { 'UPDATE': ISYupdate, 
                }


    drivers = [
            {'driver': 'GV0', 'value': 0, 'uom': 20},  #battery level
            {'driver': 'GV1', 'value': 0, 'uom': 51},  #battery level
            {'driver': 'GV2', 'value': 0, 'uom': 25},  #mode
            {'driver': 'GV3', 'value': 0, 'uom': 25},  #grid status
            {'driver': 'GV4', 'value': 0, 'uom': 25},  #on/off line
            {'driver': 'GV5', 'value': 0, 'uom': 25},  #grid services
            {'driver': 'GV6', 'value': 0, 'uom': 33},  #battery supply
            {'driver': 'GV7', 'value': 0, 'uom': 33},  #battery today
            {'driver': 'GV8', 'value': 0, 'uom': 33},  #battery yesterday
            {'driver': 'GV9', 'value': 0, 'uom': 33},  #grid supply
            {'driver': 'GV10', 'value': 0, 'uom': 33}, #grid today
            {'driver': 'GV11', 'value': 0, 'uom': 33}, #grid yesterday
            {'driver': 'GV12', 'value': 0, 'uom': 33}, #load
            {'driver': 'GV13', 'value': 0, 'uom': 33}, #consumption today
            {'driver': 'GV14', 'value': 0, 'uom': 33}, #consumption yesterday
            {'driver': 'GV15', 'value': 0, 'uom': 33}, #generation today
            {'driver': 'GV16', 'value': 0, 'uom': 33}, #generation yesterday
            {'driver': 'GV17', 'value': 0, 'uom': 33}, #grid service today
            {'driver': 'GV18', 'value': 0, 'uom': 33}, #grid service yesterday
            {'driver': 'GV19', 'value': 0, 'uom': 33}, #Solar today
            {'driver': 'GV20', 'value': 0, 'uom': 33}, #Solar yesterday
            {'driver': 'GV20', 'value': 0, 'uom': 33}, #Solar yesterday
            {'driver': 'GV21', 'value': 0, 'uom': 103}, #Current buy rate
            #{'driver': 'GV22', 'value': 0, 'uom': 103}, #Current sell rate
            {'driver': 'GV23', 'value': 99, 'uom': 25}, #Peak/Partial/offpeak
            {'driver': 'GV24', 'value': 99, 'uom': 25}, #Summer/Winter
           
           
            ]


