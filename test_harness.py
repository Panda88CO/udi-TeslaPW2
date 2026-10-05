#!/usr/bin/env python3
"""
Test Harness for udi-TeslaPW2 Polyglot Node Server.

Tests:
1. XML Profile & NLS Consistency (editors.xml, nodedefs.xml, en_us.txt)
   - Uppercase IDs without underscores
   - Reserved words exclusion (CON, TIME, BOOL)
   - Comma-only subset ranges
   - NodeDef <-> Python class mapping
   - Driver <-> Status mapping
   - Command <-> Accept mapping
2. Node Lifecycle & Driver Updates:
   - TeslaPWController
   - teslaPWStatusNode
   - teslaPWHistoryNode
   - teslaPWSetupNode
3. Node Command Handlers (STORM_MODE, OP_MODE, BACKUP_PCT, GRID_MODE, EV_CHRG_MODE, UPDATE, etc.)

Can be run:
  python3 test_harness.py           # Runs all automated tests
  python3 test_harness.py --demo    # Runs interactive simulation & displays driver tables
  python3 test_harness.py --profile # Runs profile XML validation only
"""

import sys
import os
import json
import types
import unittest
import xml.etree.ElementTree as ET
from enum import Enum

# ---------------------------------------------------------------------------
# 1. Environment & Mock Setup (Gracefully mock missing dependencies)
# ---------------------------------------------------------------------------

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Mock requests if not installed
if 'requests' not in sys.modules:
    try:
        import requests
    except ImportError:
        mock_req = types.ModuleType('requests')
        mock_req.exceptions = types.SimpleNamespace(
            HTTPError=Exception,
            RequestException=Exception,
            ConnectionError=Exception,
            Timeout=Exception,
        )
        mock_req.post = lambda *a, **k: types.SimpleNamespace(raise_for_status=lambda: None, json=lambda: {})
        mock_req.get = lambda *a, **k: types.SimpleNamespace(raise_for_status=lambda: None, json=lambda: {})
        sys.modules['requests'] = mock_req

# Mock tzlocal if not installed
if 'tzlocal' not in sys.modules:
    try:
        import tzlocal
    except ImportError:
        mock_tzl = types.ModuleType('tzlocal')
        mock_tzl.get_localzone = lambda: None
        sys.modules['tzlocal'] = mock_tzl

# Mock tesla_powerwall enums and classes if not installed
if 'tesla_powerwall' not in sys.modules:
    try:
        import tesla_powerwall
    except ImportError:
        mock_tpw_pkg = types.ModuleType('tesla_powerwall')
        class GridStatus(Enum):
            CONNECTED = 'Connected'
            ISLANDED_READY = 'IslandedReady'
            ISLANDED = 'Islanded'
            TRANSITION_TO_GRID = 'TransitionToGrid'

        class OperationMode(Enum):
            BACKUP = 'backup'
            SELF_CONSUMPTION = 'self_consumption'
            AUTONOMOUS = 'autonomous'
            SITE_CONTROL = 'site_control'

        class MeterType(Enum):
            SOLAR = 'solar'
            BATTERY = 'battery'
            LOAD = 'load'
            SITE = 'site'
            GENERATOR = 'generator'

        mock_tpw_pkg.GridStatus = GridStatus
        mock_tpw_pkg.OperationMode = OperationMode
        mock_tpw_pkg.MeterType = MeterType
        mock_tpw_pkg.Powerwall = object
        sys.modules['tesla_powerwall'] = mock_tpw_pkg


# High-fidelity Mock Node and Interface for udi_interface
class MockNodeBase:
    """Base Node mock compatible with udi_interface.Node."""
    def __init__(self, polyglot, primary, address, name):
        self.poly = polyglot
        self.primary = primary
        self.address = address
        self.name = name
        self.drivers = getattr(self.__class__, 'drivers', [])
        self.commands = getattr(self.__class__, 'commands', {})
        self.id = getattr(self.__class__, 'id', None)
        self._driver_values = {}
        self._reported_cmds = []

    def setDriver(self, key, value, report=True, force=False, uom=None):
        if not hasattr(self, '_driver_values'):
            self._driver_values = {}
        self._driver_values[key] = {
            'value': value,
            'uom': uom,
            'report': report,
            'force': force
        }

    def reportCmd(self, cmd, value=None):
        if not hasattr(self, '_reported_cmds'):
            self._reported_cmds = []
        self._reported_cmds.append((cmd, value))

    def reportDrivers(self):
        pass


class MockPolyglotInterface:
    """Mock Polyglot Interface simulating PG3 / IoX controller environment."""
    ADDNODEDONE = 'addNodeDone'
    START = 'start'
    STOP = 'stop'
    POLL = 'poll'
    CUSTOMPARAMS = 'customParams'
    CUSTOMDATA = 'customData'
    CONFIGDONE = 'configDone'
    LOGLEVEL = 'logLevel'
    NOTICES = 'notices'
    CUSTOMNS = 'customNs'
    OAUTH = 'oauth'
    PROFILE = 'getProfile'
    UPDATEPROFILEDONE = 'updateProfileDone'

    def __init__(self):
        self._nodes = {}
        self._subscriptions = {}
        self.Notices = types.SimpleNamespace(
            clear=lambda: None,
            __setitem__=lambda k, v: None,
            __getitem__=lambda k: None
        )
        self.nodes_in_db = []
        self.ready_called = 0
        self.serverdata = {'profile_version': '0.2.0'}
        self._ifaceData = types.SimpleNamespace(profile_version=None)
        self.json_profile_updates = []

    def updateJsonProfile(self, profile, options=None):
        if not isinstance(profile, dict):
            raise ValueError('Profile must be a dictionary')
        self.json_profile_updates.append(profile)
        self.publish(self.UPDATEPROFILEDONE, {'success': True, 'requestId': profile.get('requestId')})
        return {'success': True}

    def subscribe(self, event, handler, key=None):
        if event not in self._subscriptions:
            self._subscriptions[event] = []
        self._subscriptions[event].append((handler, key))

    def publish(self, event, data=None, key=None):
        if event in self._subscriptions:
            for handler, k in self._subscriptions[event]:
                if k is None or k == key:
                    if data is not None:
                        handler(data)
                    else:
                        handler()

    def addNode(self, node, conn_status=None, rename=False):
        self._nodes[node.address] = node
        if hasattr(node, 'node_queue'):
            node.node_queue({'address': node.address})

    def getNode(self, address):
        return self._nodes.get(address)

    def delNode(self, address_or_node):
        addr = address_or_node if isinstance(address_or_node, str) else getattr(address_or_node, 'address', None)
        if addr in self._nodes:
            del self._nodes[addr]

    def nodes(self):
        return list(self._nodes.values())

    def ready(self):
        self.ready_called += 1

    def stop(self):
        pass

    def getValidAddress(self, address):
        return str(address).lower()[:14]

    def getValidName(self, name):
        return str(name)[:32]

    def getNodesFromDb(self):
        return self.nodes_in_db

    def setCustomParamsDoc(self):
        pass


class MockCustom:
    def __init__(self, poly, name):
        self.poly = poly
        self.name = name
        self.data = {}
    def __setitem__(self, k, v): self.data[k] = v
    def __getitem__(self, k): return self.data.get(k)
    def clear(self): self.data.clear()
    def load(self, d): self.data = d or {}


class MockOAuthBase:
    def __init__(self, poly):
        self.poly = poly
        self.customData = MockCustom(poly, 'customdata')
        self.oauthConfig = {}


# Inject mock udi_interface into sys.modules if not already present
if 'udi_interface' not in sys.modules:
    try:
        import udi_interface
    except ImportError:
        mock_udi = types.ModuleType('udi_interface')
        mock_udi.Node = MockNodeBase
        mock_udi.Interface = MockPolyglotInterface
        mock_udi.Custom = MockCustom
        mock_udi.OAuth = MockOAuthBase
        mock_udi.LOGGER = types.SimpleNamespace(
            info=lambda *a, **k: None,
            debug=lambda *a, **k: None,
            error=lambda *a, **k: None,
            warning=lambda *a, **k: None,
        )
        sys.modules['udi_interface'] = mock_udi


# Now import node modules
from TeslaPWStatusNode import teslaPWStatusNode
from TeslaPWHistoryNode import teslaPWHistoryNode
from TeslaPWSetupNode import teslaPWSetupNode
from TeslaPW2main import TeslaPWController


# ---------------------------------------------------------------------------
# 2. Mock Tesla Powerwall Service
# ---------------------------------------------------------------------------

class MockTeslaService:
    """Simulates Tesla Powerwall API data sources (cloud & local telemetry)."""
    def __init__(self):
        self.online = True
        self.charge_level = 82.5        # %
        self.solar_supply = 4.35        # kW
        self.battery_supply = -1.25     # kW
        self.load = 2.10                # kW
        self.grid_supply = 0.00         # kW
        self.operation_mode = 1         # 0=backup, 1=self_consumption, 2=autonomous
        self.grid_status = 0            # 0=on_grid
        self.grid_services_active = 0   # 0=inactive

        # Today's energy metrics (kWh)
        self.days_consumption = 14.50
        self.days_solar = 22.10
        self.days_battery_export = 4.50
        self.days_battery_import = 6.80
        self.days_grid_export = 10.20
        self.days_grid_import = 1.40
        self.days_generator_use = 0.00

        # Yesterday's energy metrics (kWh)
        self.yesterday_consumption = 16.20
        self.yesterday_solar = 24.50
        self.yesterday_battery_export = 5.10
        self.yesterday_battery_import = 7.20
        self.yesterday_grid_export = 12.30
        self.yesterday_grid_import = 1.80
        self.yesterday_generator_use = 0.00

        # Backup & EV metrics
        self.days_backup_events = 0
        self.days_backup_time = 0
        self.yesterday_backup_events = 1
        self.yesterday_backup_time = 3600
        self.days_evcharge_power = 0.0
        self.days_evcharge_time = 0
        self.yesterday_evcharge_power = 0.0
        self.yesterday_evcharge_time = 0

        # Setup parameters
        self.backup_pct = 20.0
        self.storm_mode = 0
        self.tou_mode = 0
        self.grid_import_mode = 0
        self.grid_export_mode = 0
        self.ev_charge_reserve = 50

        # Controller flags
        self.solarInstalled = True
        self.generatorInstalled = False
        self.poll_calls = []

    # Getters
    def getTPW_onLine(self): return self.online
    def getTPW_chargeLevel(self, site_id): return self.charge_level
    def getTPW_solarSupply(self, site_id): return self.solar_supply
    def getTPW_batterySupply(self, site_id): return self.battery_supply
    def getTPW_load(self, site_id): return self.load
    def getTPW_gridSupply(self, site_id): return self.grid_supply
    def getTPW_operationMode(self, site_id): return self.operation_mode
    def getTPW_gridStatus(self, site_id): return self.grid_status
    def getTPW_gridServiceActive(self, site_id): return self.grid_services_active

    def getTPW_daysConsumption(self, site_id): return self.days_consumption
    def getTPW_daysSolar(self, site_id): return self.days_solar
    def getTPW_daysBattery_export(self, site_id): return self.days_battery_export
    def getTPW_daysBattery_import(self, site_id): return self.days_battery_import
    def getTPW_daysGrid_export(self, site_id): return self.days_grid_export
    def getTPW_daysGrid_import(self, site_id): return self.days_grid_import
    def getTPW_daysGeneratorUse(self, site_id): return self.days_generator_use

    def getTPW_yesterdayConsumption(self, site_id): return self.yesterday_consumption
    def getTPW_yesterdaySolar(self, site_id): return self.yesterday_solar
    def getTPW_yesterdayBattery_export(self, site_id): return self.yesterday_battery_export
    def getTPW_yesterdayBattery_import(self, site_id): return self.yesterday_battery_import
    def getTPW_yesterdayGrid_export(self, site_id): return self.yesterday_grid_export
    def getTPW_yesterdayGrid_import(self, site_id): return self.yesterday_grid_import
    def getTPW_yesterdayGeneratorUse(self, site_id): return self.yesterday_generator_use

    def getTPW_days_backup_events(self, site_id): return self.days_backup_events
    def getTPW_days_backup_time(self, site_id): return self.days_backup_time
    def getTPW_yesterday_backup_events(self, site_id): return self.yesterday_backup_events
    def getTPW_yesterday_backup_time(self, site_id): return self.yesterday_backup_time
    def getTPW_days_evcharge_power(self, site_id): return self.days_evcharge_power
    def getTPW_days_evcharge_time(self, site_id): return self.days_evcharge_time
    def getTPW_yesterday_evcharge_power(self, site_id): return self.yesterday_evcharge_power
    def getTPW_yesterday_evcharge_time(self, site_id): return self.yesterday_evcharge_time

    def getTPW_backoffLevel(self, site_id): return self.backup_pct
    def getTPW_stormMode(self, site_id): return self.storm_mode
    def getTPW_touMode(self, site_id): return self.tou_mode

    # Setters / Commands
    def pollSystemData(self, site_id, mode='all'):
        self.poll_calls.append((site_id, mode))
        return True

    def setTPW_operationMode(self, mode, site_id):
        self.operation_mode = mode

    def tesla_set_storm_mode(self, mode, site_id):
        self.storm_mode = mode

    def setTPW_backoffLevel(self, pct, site_id):
        self.backup_pct = pct

    def setTPW_grid_import_export(self, imp_mode, exp_mode, site_id):
        self.grid_import_mode = imp_mode
        self.grid_export_mode = exp_mode

    def setTPW_EV_offgrid_charge_reserve(self, pct, site_id):
        self.ev_charge_reserve = pct

    def disconnectTPW(self):
        self.online = False


# ---------------------------------------------------------------------------
# 3. Test Suites
# ---------------------------------------------------------------------------

class TestProfileXmlAndNls(unittest.TestCase):
    """Verifies profile XML standards and consistency with Python Node classes."""

    def setUp(self):
        profile_dir = os.path.join(ROOT_DIR, 'profile')
        if not os.path.exists(profile_dir):
            profile_dir = os.path.join(ROOT_DIR, 'profile.static')
        self.editors_xml = os.path.join(profile_dir, 'editor', 'editors.xml')
        self.nodedefs_xml = os.path.join(profile_dir, 'nodedef', 'nodedefs.xml')
        self.nls_txt = os.path.join(profile_dir, 'nls', 'en_us.txt')
        self.reserved_words = {'CON', 'TIME', 'BOOL'}

    def test_xml_files_exist_and_well_formed(self):
        self.assertTrue(os.path.exists(self.editors_xml), "editors.xml missing")
        self.assertTrue(os.path.exists(self.nodedefs_xml), "nodedefs.xml missing")
        ET.parse(self.editors_xml)
        ET.parse(self.nodedefs_xml)

    def test_editor_ids_standards(self):
        """Verifies editor IDs are uppercase, no underscores, and not reserved."""
        tree = ET.parse(self.editors_xml)
        seen_ids = set()
        for editor in tree.getroot().findall('editor'):
            eid = editor.attrib.get('id', '').strip()
            self.assertTrue(eid, "Editor missing id attribute")
            self.assertNotIn(eid, seen_ids, f"Duplicate editor ID: {eid}")
            seen_ids.add(eid)

            self.assertEqual(eid, eid.upper(), f"Editor ID '{eid}' is not all uppercase")
            self.assertNotIn('_', eid, f"Editor ID '{eid}' contains underscore")
            self.assertNotIn(eid, self.reserved_words, f"Editor ID '{eid}' is a reserved word")

    def test_editor_subsets_comma_only(self):
        """Verifies subset definitions do not use range hyphens and only use commas."""
        tree = ET.parse(self.editors_xml)
        for editor in tree.getroot().findall('editor'):
            eid = editor.attrib.get('id', '')
            for r in editor.findall('range'):
                subset = r.attrib.get('subset')
                if subset is not None:
                    self.assertNotIn('-', subset, f"Editor '{eid}' subset has range hyphen: '{subset}'")
                    parts = [p.strip() for p in subset.split(',')]
                    for p in parts:
                        self.assertTrue(p.isdigit(), f"Editor '{eid}' non-integer subset value: '{p}'")

    def test_nodedef_ids_standards(self):
        """Verifies nodeDef IDs are uppercase, no underscores, and not reserved."""
        tree = ET.parse(self.nodedefs_xml)
        seen_ids = set()
        for nd in tree.getroot().findall('nodeDef'):
            nid = nd.attrib.get('id', '').strip()
            self.assertTrue(nid, "NodeDef missing id attribute")
            self.assertNotIn(nid, seen_ids, f"Duplicate nodeDef ID: {nid}")
            seen_ids.add(nid)

            self.assertEqual(nid, nid.upper(), f"NodeDef ID '{nid}' is not all uppercase")
            self.assertNotIn('_', nid, f"NodeDef ID '{nid}' contains underscore")
            self.assertNotIn(nid, self.reserved_words, f"NodeDef ID '{nid}' is a reserved word")

    def test_nodedef_editor_references_exist(self):
        """Verifies every editor referenced in nodedefs.xml exists in editors.xml."""
        ed_tree = ET.parse(self.editors_xml)
        editor_ids = {e.attrib.get('id', '').strip() for e in ed_tree.getroot().findall('editor')}

        nd_tree = ET.parse(self.nodedefs_xml)
        for nd in nd_tree.getroot().findall('nodeDef'):
            nid = nd.attrib.get('id')
            for st in nd.findall('.//st'):
                ed_ref = st.attrib.get('editor', '').strip()
                if ed_ref:
                    self.assertIn(ed_ref, editor_ids, f"NodeDef '{nid}' references missing editor '{ed_ref}'")
            for p in nd.findall('.//p'):
                ed_ref = p.attrib.get('editor', '').strip()
                if ed_ref:
                    self.assertIn(ed_ref, editor_ids, f"NodeDef '{nid}' param references missing editor '{ed_ref}'")

    def test_nls_entries_match_nodedefs(self):
        """Verifies en_us.txt has ND-<id>-NAME and ND-<id>-ICON for each nodedef."""
        nd_tree = ET.parse(self.nodedefs_xml)
        nodedef_ids = {nd.attrib.get('id', '').strip() for nd in nd_tree.getroot().findall('nodeDef')}

        with open(self.nls_txt, 'r') as f:
            nls_content = f.read()

        for nid in nodedef_ids:
            self.assertIn(f"ND-{nid}-NAME", nls_content, f"Missing ND-{nid}-NAME in en_us.txt")
            self.assertIn(f"ND-{nid}-ICON", nls_content, f"Missing ND-{nid}-ICON in en_us.txt")

    def test_python_nodes_match_nodedefs(self):
        """Verifies Python Node class IDs match nodedef IDs in nodedefs.xml."""
        nd_tree = ET.parse(self.nodedefs_xml)
        nodedef_ids = {nd.attrib.get('id', '').strip() for nd in nd_tree.getroot().findall('nodeDef')}

        self.assertIn(TeslaPWController.id, nodedef_ids)
        self.assertIn(teslaPWStatusNode.id, nodedef_ids)
        self.assertIn(teslaPWHistoryNode.id, nodedef_ids)
        self.assertIn(teslaPWSetupNode.id, nodedef_ids)

    def test_python_drivers_match_nodedefs_and_editors(self):
        """Verifies that Python node drivers match nodedefs.xml and editors.xml."""
        ed_tree = ET.parse(self.editors_xml)
        editors = {}
        for ed in ed_tree.getroot().findall('editor'):
            eid = ed.attrib['id'].strip()
            editors[eid] = [r.attrib.get('uom') for r in ed.findall('range') if 'uom' in r.attrib]

        nd_tree = ET.parse(self.nodedefs_xml)
        nodedefs = {}
        for nd in nd_tree.getroot().findall('nodeDef'):
            nid = nd.attrib['id'].strip()
            sts = {st.attrib['id'].strip(): st.attrib.get('editor', '').strip() for st in nd.findall('.//st')}
            nodedefs[nid] = sts

        node_classes = {
            'CONTROLLER': TeslaPWController,
            'PWSTATUS': teslaPWStatusNode,
            'PWHISTORY': teslaPWHistoryNode,
            'PWSETUP': teslaPWSetupNode,
        }

        for nid, cls in node_classes.items():
            nd_sts = nodedefs.get(nid, {})
            py_drivers = {d['driver']: str(d.get('uom', '')) for d in getattr(cls, 'drivers', [])}

            # 1. No extraneous drivers in Python that don't exist in nodedefs.xml
            extra_in_py = set(py_drivers.keys()) - set(nd_sts.keys())
            self.assertFalse(extra_in_py, f"{nid} defines drivers in Python not in nodedefs.xml: {extra_in_py}")

            # 2. No drivers in nodedefs.xml missing from Python drivers list
            missing_in_py = set(nd_sts.keys()) - set(py_drivers.keys())
            self.assertFalse(missing_in_py, f"{nid} missing drivers in Python defined in nodedefs.xml: {missing_in_py}")

            # 3. UOM in Python driver must be valid for the editor in editors.xml
            for drv, py_uom in py_drivers.items():
                ed_id = nd_sts.get(drv)
                if ed_id and ed_id in editors:
                    allowed_uoms = editors[ed_id]
                    self.assertIn(
                        py_uom,
                        allowed_uoms,
                        f"{nid} driver '{drv}' has uom={py_uom} in Python, but editor '{ed_id}' only allows uoms={allowed_uoms}"
                    )


class TestTeslaPWStatusNode(unittest.TestCase):
    """Tests the Powerwall Status Node functionality."""

    def setUp(self):
        self.poly = MockPolyglotInterface()
        self.tpw = MockTeslaService()
        self.site_id = 'site_12345678'
        self.node = teslaPWStatusNode(
            self.poly, 'controller', 'pwstatus', 'Power Wall Status', self.site_id, self.tpw
        )

    def test_node_registration_and_id(self):
        self.assertEqual(self.node.id, 'PWSTATUS')
        self.assertEqual(self.node.address, 'pwstatus')
        self.assertIs(self.poly.getNode('pwstatus'), self.node)

    def test_nodes_do_not_call_poly_ready(self):
        """Verifies that node instantiation does not invoke polyglot.ready()."""
        self.assertEqual(self.poly.ready_called, 0, "Nodes should not call poly.ready()")

    def test_start_creates_subnodes(self):
        self.node.start()
        self.assertTrue(self.node.node_ready())

        # Check subnodes created
        sub_adr = 'controller'[-8:]
        setup_node = self.poly.getNode('setup_' + sub_adr)
        hist_node = self.poly.getNode('hist_' + sub_adr)
        self.assertIsNotNone(setup_node, "Setup sub-node was not created")
        self.assertIsNotNone(hist_node, "History sub-node was not created")
        self.assertEqual(setup_node.id, 'PWSETUP')
        self.assertEqual(hist_node.id, 'PWHISTORY')

    def test_update_drivers_online(self):
        self.node.start()
        drivers = self.node._driver_values

        self.assertEqual(drivers['ST']['value'], 1)                  # Online
        self.assertEqual(drivers['GV0']['value'], 82.5)               # Battery %
        self.assertEqual(drivers['GV1']['value'], 4.35)               # Solar kW
        self.assertEqual(drivers['GV2']['value'], -1.25)              # Battery kW
        self.assertEqual(drivers['GV3']['value'], 2.10)               # Home load kW
        self.assertEqual(drivers['GV4']['value'], 0.00)               # Grid supply kW
        self.assertEqual(drivers['GV5']['value'], 1)                  # Operation Mode
        self.assertEqual(drivers['GV6']['value'], 0)                  # Grid Status (on grid)
        self.assertEqual(drivers['GV8']['value'], 14.50)              # Home total use today
        self.assertEqual(drivers['GV9']['value'], 22.10)              # Solar export today
        self.assertEqual(drivers['GV10']['value'], 4.50)              # Battery export today
        self.assertEqual(drivers['GV11']['value'], 6.80)              # Battery import today
        self.assertEqual(drivers['GV12']['value'], 10.20)             # Grid export today
        self.assertEqual(drivers['GV13']['value'], 1.40)              # Grid import today
        # Net grid = 10.20 - 1.40 = 8.80
        self.assertAlmostEqual(drivers['GV14']['value'], 8.80, places=2)

    def test_update_drivers_offline(self):
        self.tpw.online = False
        self.node.start()
        self.assertEqual(self.node._driver_values['ST']['value'], 0)

    def test_isy_update_command(self):
        self.node.start()
        self.node.ISYupdate({'cmd': 'UPDATE'})
        self.assertIn((self.site_id, 'all'), self.tpw.poll_calls)


class TestTeslaPWSetupNode(unittest.TestCase):
    """Tests the Powerwall Control Parameters (Setup) Node."""

    def setUp(self):
        self.poly = MockPolyglotInterface()
        self.tpw = MockTeslaService()
        self.site_id = 'site_12345678'
        self.node = teslaPWSetupNode(
            self.poly, 'pwstatus', 'pwsetup', 'Control Parameters', self.site_id, self.tpw
        )
        self.node.start()

    def test_node_id_and_initial_drivers(self):
        self.assertEqual(self.node.id, 'PWSETUP')
        self.assertEqual(self.node._driver_values['GV1']['value'], 20.0)  # Backup %
        self.assertEqual(self.node._driver_values['GV2']['value'], 1)     # Op mode
        self.assertEqual(self.node._driver_values['GV3']['value'], 0)     # Storm mode

    def test_command_storm_mode(self):
        self.node.setStormMode({'value': '1'})
        self.assertEqual(self.tpw.storm_mode, 1)
        self.assertEqual(self.node._driver_values['GV3']['value'], 1)

        self.node.setStormMode({'value': '0'})
        self.assertEqual(self.tpw.storm_mode, 0)
        self.assertEqual(self.node._driver_values['GV3']['value'], 0)

    def test_command_op_mode(self):
        self.node.setOperatingMode({'value': '2'})  # autonomous
        self.assertEqual(self.tpw.operation_mode, 2)
        self.assertEqual(self.node._driver_values['GV2']['value'], 2)

    def test_command_backup_percent(self):
        self.node.setBackupPercent({'value': '35.5'})
        self.assertEqual(self.tpw.backup_pct, 35.5)
        self.assertEqual(self.node._driver_values['GV1']['value'], 35.5)

    def test_command_grid_mode(self):
        self.node.set_grid_mode({
            'query': {
                'import.uom25': '1',
                'export.uom25': '2'
            }
        })
        self.assertEqual(self.tpw.grid_import_mode, 1)
        self.assertEqual(self.tpw.grid_export_mode, 2)
        self.assertEqual(self.node._driver_values['GV5']['value'], 1)
        self.assertEqual(self.node._driver_values['GV6']['value'], 2)

    def test_command_ev_charge_reserve(self):
        self.node.set_EV_charge_reserve({'value': '70'})
        self.assertEqual(self.tpw.ev_charge_reserve, 70)
        self.assertEqual(self.node._driver_values['GV7']['value'], 70)


class TestTeslaPWHistoryNode(unittest.TestCase):
    """Tests the Powerwall Usage History Node."""

    def setUp(self):
        self.poly = MockPolyglotInterface()
        self.tpw = MockTeslaService()
        self.site_id = 'site_12345678'
        self.node = teslaPWHistoryNode(
            self.poly, 'pwstatus', 'pwhistory', 'Usage History', self.site_id, self.tpw
        )
        self.node.start()

    def test_node_id_and_initial_drivers(self):
        self.assertEqual(self.node.id, 'PWHISTORY')
        drivers = self.node._driver_values

        self.assertEqual(drivers['ST']['value'], 1)
        # Today
        self.assertEqual(drivers['GV8']['value'], 14.50)
        self.assertEqual(drivers['GV9']['value'], 22.10)
        self.assertEqual(drivers['GV10']['value'], 4.50)
        self.assertEqual(drivers['GV11']['value'], 6.80)
        self.assertEqual(drivers['GV12']['value'], 10.20)
        self.assertEqual(drivers['GV13']['value'], 1.40)
        self.assertAlmostEqual(drivers['GV14']['value'], 8.80, places=2)

        # Yesterday
        self.assertEqual(drivers['GV15']['value'], 16.20)
        self.assertEqual(drivers['GV16']['value'], 24.50)
        self.assertEqual(drivers['GV17']['value'], 5.10)
        self.assertEqual(drivers['GV18']['value'], 7.20)
        self.assertEqual(drivers['GV19']['value'], 12.30)
        self.assertEqual(drivers['GV20']['value'], 1.80)
        self.assertAlmostEqual(drivers['GV21']['value'], 10.50, places=2)

        # Backup events & EV charge
        self.assertEqual(drivers['GV22']['value'], 0)
        self.assertEqual(drivers['GV23']['value'], 0)
        self.assertEqual(drivers['GV24']['value'], 1)
        self.assertEqual(drivers['GV25']['value'], 3600)


class TestTeslaPWController(unittest.TestCase):
    """Tests the Main Controller Node."""

    def setUp(self):
        self.poly = MockPolyglotInterface()
        self.mock_cloud = types.SimpleNamespace(
            customDataHandlerDone=True,
            customNsHandler=lambda *a: None,
            oauthHandler=lambda *a: None
        )
        self.controller = TeslaPWController(
            self.poly, 'controller', 'controller', 'Tesla PowerWall Info', self.mock_cloud
        )
        self.controller.node = self.controller

    def test_controller_id(self):
        self.assertEqual(self.controller.id, 'CONTROLLER')

    def test_controller_heartbeat(self):
        self.controller.hb = 0
        self.controller.heartbeat()
        self.assertEqual(self.controller._reported_cmds[-1], ('DON', 2))
        self.assertEqual(self.controller.hb, 1)

        self.controller.heartbeat()
        self.assertEqual(self.controller._reported_cmds[-1], ('DOF', 2))
        self.assertEqual(self.controller.hb, 0)

    def test_controller_update_isy_drivers(self):
        self.controller.TPW = MockTeslaService()
        self.controller.cloudAccessUp = True
        self.controller.updateISYdrivers()

        drivers = self.controller._driver_values
        self.assertEqual(drivers['ST']['value'], 1)   # Controller UP
        self.assertEqual(drivers['GV2']['value'], 1)  # TPW Connected
        self.assertEqual(drivers['GV3']['value'], 0)  # Missed polls
        self.assertEqual(drivers['GV4']['value'], 0)  # Cloud/Local mode


class TestDynamicJsonProfile(unittest.TestCase):
    """Verifies PG3x / IoX Dynamic JSON profile generation and node server integration."""

    def setUp(self):
        self.base_profile_path = os.path.join(ROOT_DIR, 'data', 'base_profile.json')
        self.reserved_words = {'CON', 'TIME', 'BOOL'}

    def test_base_profile_json_exists_and_valid(self):
        self.assertTrue(os.path.exists(self.base_profile_path), "data/base_profile.json does not exist")
        with open(self.base_profile_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.assertIn('editors', data)
        self.assertIn('nodedefs', data)
        self.assertIn('nls', data)
        self.assertGreaterEqual(len(data['editors']), 28)
        self.assertEqual(len(data['nodedefs']), 4)
        self.assertGreaterEqual(len(data['nls']), 130)

    def test_dynamic_editors_standards(self):
        """Verifies dynamic JSON editors comply with PG3x conventions (uppercase, no underscore, no reserved words)."""
        with open(self.base_profile_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        seen = set()
        for ed in data['editors']:
            eid = ed.get('id', '')
            self.assertTrue(eid, "Editor missing id")
            self.assertNotIn(eid, seen, f"Duplicate editor ID: {eid}")
            seen.add(eid)
            self.assertEqual(eid, eid.upper(), f"Editor ID '{eid}' is not uppercase")
            self.assertNotIn('_', eid, f"Editor ID '{eid}' contains underscore")
            self.assertNotIn(eid, self.reserved_words, f"Editor ID '{eid}' is reserved word")
            for r in ed.get('range', []):
                subset = r.get('subset')
                if subset is not None:
                    self.assertNotIn('-', str(subset), f"Editor '{eid}' subset has range hyphen: '{subset}'")
                    parts = [p.strip() for p in str(subset).split(',')]
                    for p in parts:
                        self.assertTrue(p.isdigit(), f"Editor '{eid}' non-integer subset value: '{p}'")

    def test_dynamic_nodedefs_standards(self):
        """Verifies dynamic JSON nodedefs reference valid editors and follow naming rules."""
        with open(self.base_profile_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        editor_ids = {e['id'] for e in data['editors']}
        seen = set()
        for nd in data['nodedefs']:
            nid = nd.get('id', '')
            self.assertTrue(nid, "NodeDef missing id")
            self.assertNotIn(nid, seen, f"Duplicate nodeDef ID: {nid}")
            seen.add(nid)
            self.assertEqual(nid, nid.upper(), f"NodeDef ID '{nid}' is not uppercase")
            self.assertNotIn('_', nid, f"NodeDef ID '{nid}' contains underscore")
            self.assertNotIn(nid, self.reserved_words, f"NodeDef ID '{nid}' is reserved word")
            for st in nd.get('sts', []):
                ed_ref = st.get('editor')
                if ed_ref:
                    self.assertIn(ed_ref, editor_ids, f"NodeDef '{nid}' references missing editor '{ed_ref}'")
            for cmd in nd.get('cmds', {}).get('accepts', []):
                for p in cmd.get('params', []):
                    ed_ref = p.get('editor')
                    if ed_ref:
                        self.assertIn(ed_ref, editor_ids, f"NodeDef '{nid}' param references missing editor '{ed_ref}'")

    def test_dynamic_nls_covers_nodedefs(self):
        """Verifies dynamic JSON NLS entries contain name and icon for each nodedef."""
        with open(self.base_profile_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        nls = data['nls']
        for nd in data['nodedefs']:
            nid = nd['id']
            self.assertIn(f"ND-{nid}-NAME", nls, f"Missing ND-{nid}-NAME in dynamic NLS")
            self.assertIn(f"ND-{nid}-ICON", nls, f"Missing ND-{nid}-ICON in dynamic NLS")

    def test_controller_dynamic_profile_update(self):
        """Tests controller update_dynamic_profile calling updateJsonProfile with version caching."""
        poly = MockPolyglotInterface()
        mock_cloud = types.SimpleNamespace(
            customDataHandlerDone=True,
            customNsHandler=lambda *a: None,
            oauthHandler=lambda *a: None
        )
        controller = TeslaPWController(poly, 'controller', 'controller', 'Tesla PowerWall Info', mock_cloud)
        controller.node = controller
        
        self.assertEqual(len(poly.json_profile_updates), 0)
        self.assertIsNone(poly._ifaceData.profile_version)

        # First call: sends updateJsonProfile and records version
        controller.update_dynamic_profile()
        self.assertEqual(len(poly.json_profile_updates), 1)
        self.assertEqual(poly._ifaceData.profile_version, '0.2.0')

        # Second call (idempotent): should NOT re-send because version is identical
        controller.update_dynamic_profile()
        self.assertEqual(len(poly.json_profile_updates), 1)

        # Forced update: sends updateJsonProfile even when version matches
        controller.update_dynamic_profile(force=True)
        self.assertEqual(len(poly.json_profile_updates), 2)

    def test_update_profile_done_handler(self):
        """Tests controller updateProfileDoneHandler runs without exception."""
        poly = MockPolyglotInterface()
        mock_cloud = types.SimpleNamespace(
            customDataHandlerDone=True,
            customNsHandler=lambda *a: None,
            oauthHandler=lambda *a: None
        )
        controller = TeslaPWController(poly, 'controller', 'controller', 'Tesla PowerWall Info', mock_cloud)
        controller.updateProfileDoneHandler({'success': True, 'requestId': 'test1234'})


# ---------------------------------------------------------------------------
# 4. Interactive Demonstration / Simulation Runner
# ---------------------------------------------------------------------------

def run_simulation_demo():
    """Runs a simulated live session demonstrating all nodes and driver tables."""
    print("=" * 70)
    print("Tesla Powerwall Node Server - Interactive Simulation Harness")
    print("=" * 70)

    poly = MockPolyglotInterface()
    tpw = MockTeslaService()
    site_id = "site_energy_998877"

    print("\n[1] Initializing Status Node...")
    st_node = teslaPWStatusNode(poly, 'controller', 'pwstatus', 'Tesla Powerwall', site_id, tpw)
    st_node.start()

    sub_adr = 'controller'[-8:]
    setup_node = poly.getNode('setup_' + sub_adr)
    hist_node = poly.getNode('hist_' + sub_adr)
    if setup_node:
        setup_node.start()
    if hist_node:
        hist_node.start()

    # Parse en_us.txt or base_profile.json for driver descriptions
    nls_names = {}
    base_json_path = os.path.join(ROOT_DIR, 'data', 'base_profile.json')
    if os.path.exists(base_json_path):
        with open(base_json_path, 'r', encoding='utf-8') as f:
            prof_data = json.load(f)
            for k, v in prof_data.get('nls', {}).items():
                if k.startswith('ST-'):
                    parts = k.split('-')
                    if len(parts) >= 3:
                        nls_names[(parts[1], parts[2])] = v
    else:
        for cand in ['profile', 'profile.static']:
            nls_path = os.path.join(ROOT_DIR, cand, 'nls', 'en_us.txt')
            if os.path.exists(nls_path):
                with open(nls_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if '=' in line and line.strip().startswith('ST-'):
                            k, v = line.split('=', 1)
                            parts = k.strip().split('-')
                            if len(parts) >= 3:
                                nls_names[(parts[1], parts[2])] = v.strip()
                break

    nls_tags = {'PWSTATUS': 'nlspwstatus', 'PWSETUP': 'nlspwsetup', 'PWHISTORY': 'nlspwhist', 'CONTROLLER': 'nlscontroller'}

    def print_node_table(node, title):
        print(f"\n--- {title} (ID: {node.id}, Address: {node.address}) ---")
        print(f"{'Driver':<7} | {'Description':<28} | {'Value':<10} | {'UOM':<6}")
        print("-" * 60)
        tag = nls_tags.get(node.id, '')
        for drv, info in sorted(node._driver_values.items()):
            desc = nls_names.get((tag, drv), drv)[:28]
            uom_str = str(info['uom']) if info['uom'] is not None else '-'
            val_str = str(info['value'])
            print(f"{drv:<7} | {desc:<28} | {val_str:<10} | {uom_str:<6}")

    print_node_table(st_node, "Status Node Live Telemetry")
    if setup_node:
        print_node_table(setup_node, "Setup Node Control Parameters")
    if hist_node:
        print_node_table(hist_node, "History Node Usage History")

    print("\n[2] Simulating ISY Commands to Setup Node...")
    print("  -> Setting Storm Mode to ENABLED (1)")
    setup_node.setStormMode({'value': '1'})

    print("  -> Adjusting Backup Reserve to 40.0%")
    setup_node.setBackupPercent({'value': '40.0'})

    print("  -> Setting Operating Mode to Autonomous (2)")
    setup_node.setOperatingMode({'value': '2'})

    print("\nUpdated Setup Node Drivers:")
    print_node_table(setup_node, "Setup Node (Post-Command)")

    print("\n[3] Simulating Grid Outage Event...")
    tpw.grid_status = 2     # Islanded (off-grid)
    tpw.solar_supply = 0.0
    tpw.grid_supply = 0.0
    tpw.battery_supply = 2.1  # Battery discharging to power home
    st_node.updateISYdrivers()

    print_node_table(st_node, "Status Node (During Outage)")

    print("\nSimulation successfully completed!")
    print("=" * 70)


# ---------------------------------------------------------------------------
# 5. CLI Entrypoint
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    if '--demo' in sys.argv or '--interactive' in sys.argv:
        run_simulation_demo()
    elif '--profile' in sys.argv:
        suite = unittest.TestLoader().loadTestsFromTestCase(TestProfileXmlAndNls)
        unittest.TextTestRunner(verbosity=2).run(suite)
    else:
        print("Running Tesla Powerwall Node Test Harness...")
        unittest.main(verbosity=2)
