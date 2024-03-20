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
    from  udiYolinkLib import node_queue, wait_for_node_done, mask2key

    def __init__(self, polyglot, primary, address, name, TPW, site_id):
        super(teslaPWSetupNode, self).__init__(polyglot, primary, address, name)

        logging.info('_init_ Tesla Power Wall setup Node')
        self.poly = polyglot
        self.ISYforced = False
        self.TPW = TPW
        self.address = address 
        self_site_id = site_id
        self.poly.ready()
        self.poly.addNode(self, conn_status = None, rename = True)
        self.wait_for_node_done()
        self.node = self.poly.getNode(address)

    def start(self):
        logging.info('Starting Setup Node')

    def updateISYdrivers(self, level):
        if self.TPW.systemReady:
            logging.debug('Node updateISYdrivers')
            self.node.setDriver('GV1', self.TPW.getTPW_backoffLevel(self.site_id))
            self.node.setDriver('GV2', self.TPW.getTPW_operationMode(self.site_id))
            self.node.setDriver('GV3', self.TPW.getTPW_stormMode(self.site_id))
            self.node.setDriver('GV4', self.TPW.getTPW_touMode(self.site_id))


            logging.debug('updateISYdrivers - setupnode DONE')
        else:
            logging.debug('System Not ready yet')



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

    def setWeekendOffpeakStart(self, command):
        logging.debug('setWeekendOffpeakStart')
        value = int(command.get('value'))
        self.TPW.setTPW_updateTouSchedule('off_peak', 'weekend', 'start', value)
        self.node.setDriver('GV5', value)

    def setWeekendOffpeakEnd(self, command):
        logging.debug('setWeekendOffpeakEnd')
        value = int(command.get('value'))
        self.TPW.setTPW_updateTouSchedule('off_peak', 'weekend', 'end', value)
        self.node.setDriver('GV6', value)

    def setWeekendPeakStart(self, command):
        logging.debug('setWeekendPeakStart')
        value = int(command.get('value'))
        self.TPW.setTPW_updateTouSchedule('peak', 'weekend', 'start', value)
        self.node.setDriver('GV7', value)

    def setWeekendPeakEnd(self, command):
        logging.debug('setWeekendPeakEnd')
        value = int(command.get('value'))
        self.TPW.setTPW_updateTouSchedule('peak', 'weekend', 'end', value)
        self.node.setDriver('GV8', value)

    def setWeekOffpeakStart(self, command):
        logging.debug('setWeekOffpeakStart')
        value = int(command.get('value'))
        self.TPW.setTPW_updateTouSchedule('off_peak', 'week', 'start', value)
        self.node.setDriver('GV9', value)

    def setWeekOffpeakEnd(self, command):
        logging.debug('setWeekOffpeakEnd')
        value = int(command.get('value'))
        self.TPW.setTPW_updateTouSchedule('off_peak', 'week', 'end', value)
        self.node.setDriver('GV10', value)

    def setWeekPeakStart(self, command):
        logging.debug('setWeekPeakStart')
        value = int(command.get('value'))
        self.TPW.setTPW_updateTouSchedule('peak', 'week', 'start', value)
        self.node.setDriver('GV11', value)

    def setWeekPeakEnd(self, command):
        logging.debug('setWeekPeakEnd')
        value = int(command.get('value'))
        self.TPW.setTPW_updateTouSchedule('peak', 'week', 'end', value)
        self.node.setDriver('GV12', value)


    def ISYupdate (self, command):
        logging.debug('ISY-update called  Setup Node')
        if self.TPW.pollSystemData('all'):
            self.updateISYdrivers('all')
            #self.reportDrivers()
 

    id = 'pwsetup'
    commands = { 'UPDATE': ISYupdate
                ,'BACKUP_PCT' : setBackupPercent
                ,'STORM_MODE' :setStormMode
                ,'OP_MODE': setOperatingMode
                ,'TOU_MODE':setTOUmode
                #,'WE_O_PEAK_START': setWeekendOffpeakStart
                #,'WE_O_PEAK_END':setWeekendOffpeakEnd
                #,'WE_PEAK_START':setWeekendPeakStart
                #,'WE_PEAK_END':setWeekendPeakEnd
                #,'WK_O_PEAK_START':setWeekOffpeakStart
                #,'WK_O_PEAK_END':setWeekOffpeakEnd
                #,'WK_PEAK_START':setWeekPeakStart
                #,'WK_PEAK_END':setWeekPeakEnd

                }

    drivers = [
            {'driver': 'GV1', 'value': 0, 'uom': 51},  #backup reserve
            {'driver': 'GV2', 'value': 0, 'uom': 25},  #operating mode
            {'driver': 'GV3', 'value': 0, 'uom': 25},  #storm mode
            {'driver': 'GV4', 'value': 0, 'uom': 25},  #time of use mode
            {'driver': 'GV5', 'value': 0, 'uom': 58},  #weekend off start
            {'driver': 'GV6', 'value': 0, 'uom': 58},  #weekend off end
            {'driver': 'GV7', 'value': 0, 'uom': 58},  #weekend on start
            {'driver': 'GV8', 'value': 0, 'uom': 58},  #weekend on end
            {'driver': 'GV9', 'value': 0, 'uom': 58},  #weekday off start
            {'driver': 'GV10', 'value': 0, 'uom': 58}, #weekday off end
            {'driver': 'GV11', 'value': 0, 'uom': 58}, #weekday on start
            {'driver': 'GV12', 'value': 0, 'uom': 58}, #weekday on end
            ]

        

