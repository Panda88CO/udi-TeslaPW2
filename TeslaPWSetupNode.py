#!/usr/bin/env python3

import time

try:
    import udi_interface
    logging = udi_interface.LOGGER
    Custom = udi_interface.Custom
except ImportError:
    import logging
    logging.basicConfig(level=30)

               
class teslaPWSetupNode(udi_interface.Node):
    from  udiLib import node_queue, wait_for_node_done, mask2key

    def __init__(self, polyglot, primary, address, name, TPW):
        super(teslaPWSetupNode, self).__init__(polyglot, primary, address, name)

        logging.info('_init_ Tesla Power Wall setup Node')
        self.poly = polyglot
        self.ISYforced = False
        self.TPW = TPW
        self.node_ok = False
        self.address = address 
        #self_site_id = site_id
        self.n_queue = []
        self.poly.subscribe(self.poly.ADDNODEDONE, self.node_queue)
        self.poly.subscribe(self.poly.START, self.start, address)
        self.poly.ready()
        self.poly.addNode(self, conn_status = None, rename = True)
        self.wait_for_node_done()
        self.node = self.poly.getNode(address)

    def start(self):
        logging.info('Starting Setup Node')
        self.updateISYdrivers()
        self.node_ok = True

    def updateISYdrivers(self):
        logging.debug('Node updateISYdrivers')
        self.node.setDriver('GV1', self.TPW.getTPW_backoffLevel())
        self.node.setDriver('GV2', self.TPW.getTPW_operationMode())
        self.node.setDriver('GV3', self.TPW.getTPW_stormMode())
        self.node.setDriver('GV4', self.TPW.getTPW_touMode())

    def node_ready(self):
        return(self.node_ok)

    def update_PW_data(self, level):
        pass 

    def setStormMode(self, command):
        logging.debug('setStormMode')
        value = int(command.get('value'))
        self.TPW.setTPW_stormMode(value)
        self.node.setDriver('GV3', value)
        
    def setOperatingMode(self, command):
        logging.debug('setOperatingMode')
        value = int(command.get('value'))
        self.TPW.setTPW_operationMode(value)
        self.node.setDriver('GV2', value)
    
    def setBackupPercent(self, command):
        logging.debug('setBackupPercent')
        value = float(command.get('value'))
        self.TPW.setTPW_backoffLevel(value)
        self.node.setDriver('GV1', value)

    def setTOUmode(self, command):
        logging.debug('setTOUmode')
        value = int(command.get('value'))
        self.TPW.setTPW_touMode(value)
        self.node.setDriver('GV4', value)
    
    def set_grid_mode(self, command):
        logging.info('set_grid_mode{}'.format(command))
        query = command.get("query")
        imp_mode = int(query.get("import.uom25"))
        exp_mode = int(query.get("export.uom25"))
        self.TPW.setTPW_import_export_op(imp_mode, exp_mode)   

        self.node.setDriver('GV5', int(query.get("import.uom25")))
        self.node.setDriver('GV6', exp_mode)

    def set_EV_charge_reserve(self, command):
        logging.debug('set_EV_charge_reserve')
        value = int(command.get('value'))
        self.TPW.setTPW_EV_charge_limit(value)
        self.node.setDriver('GV7', value)


    def ISYupdate (self, command):
        logging.debug('ISY-update called  Setup Node')
        #if self.TPW.pollSystemData():
        self.updateISYdrivers()
            #self.reportDrivers()
 

    id = 'pwsetup'
    commands = { 'UPDATE': ISYupdate
                ,'BACKUP_PCT'   : setBackupPercent
                ,'STORM_MODE'   :setStormMode
                ,'OP_MODE'      : setOperatingMode
                ,'TOU_MODE'     :setTOUmode
                ,'GRID_MODE'    : set_grid_mode
                ,'EV_CHRG_MODE' : set_EV_charge_reserve


                }

    drivers = [
            {'driver': 'GV1', 'value': 0, 'uom': 51},  #backup reserve
            {'driver': 'GV2', 'value': 0, 'uom': 25},  #operating mode
            {'driver': 'GV3', 'value': 0, 'uom': 25},  #storm mode
            {'driver': 'GV4', 'value': 0, 'uom': 25},  #time of use mode
            {'driver': 'GV5', 'value': 0, 'uom': 25},  #grid import 
            {'driver': 'GV6', 'value': 0, 'uom': 25},  #grid export
            {'driver': 'GV7', 'value': 0, 'uom': 25},  #EV charge limit
            ]

        

