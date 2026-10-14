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
        class MockRequestException(IOError):
            def __init__(self, *args, response=None, **kwargs):
                super().__init__(*args)
                self.response = response

        class MockHTTPError(MockRequestException):
            pass

        class MockConnectionError(MockRequestException):
            pass

        class MockTimeout(MockRequestException):
            pass

        class MockJSONDecodeError(ValueError):
            pass

        mock_req.exceptions = types.SimpleNamespace(
            RequestException=MockRequestException,
            HTTPError=MockHTTPError,
            ConnectionError=MockConnectionError,
            Timeout=MockTimeout,
            JSONDecodeError=MockJSONDecodeError,
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
        self.Notices = MockCustom(self, 'notices')
        self.nodes_in_db = []
        self.ready_called = 0
        self.serverdata = {'profile_version': PROFILE_VERSION}
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

    def db_getNodeDrivers(self, address):
        return []

    def send(self, message, topic=''):
        pass

    def setCustomParamsDoc(self):
        pass


class MockCustom(dict):
    def __init__(self, poly, name):
        super().__init__()
        self.poly = poly
        self.name = name
    def delete(self, k): self.pop(k, None)
    def load(self, d, save=False):
        self.clear()
        if d: self.update(d)


class MockOAuthBase:
    def __init__(self, poly):
        self.poly = poly
        self.customData = MockCustom(poly, 'customdata')
        self._oauthTokens = MockCustom(poly, 'oauthTokens')
        self._oauthConfig = MockCustom(poly, 'oauth')
        self._oauthConfigInitialized = False

    def customNsHandler(self, key, data):
        if key == 'oauth':
            self._oauthConfigInitialized = True
            self._oauthConfig.load(data)
        elif key == 'oauthTokens':
            self._oauthTokens.load(data)
        return True

    def oauthHandler(self, token):
        self._oauthTokens.load(token)
        return True

    def _setExpiry(self, token):
        from datetime import datetime, timedelta
        if 'expires_in' in token:
            token['expiry'] = (datetime.now() + timedelta(seconds=token['expires_in'])).isoformat()

    def getAccessToken(self):
        if self._oauthTokens and self._oauthTokens.get('access_token'):
            return self._oauthTokens.get('access_token')
        raise ValueError('Access token is not available')

    def updateOauthSettings(self, update):
        if hasattr(self, '_oauthConfig') and isinstance(update, dict):
            self._oauthConfig.update(update)

    def getOauthSettings(self):
        return dict(self._oauthConfig)


# Inject mock udi_interface into sys.modules if not already present
if 'udi_interface' not in sys.modules:
    try:
        import udi_interface
        _orig_setDriver = udi_interface.Node.setDriver
        def _mock_setDriver(self, key, value, report=True, force=False, uom=None):
            if not hasattr(self, '_driver_values'):
                self._driver_values = {}
            self._driver_values[key] = {'value': value, 'uom': uom, 'report': report, 'force': force}
            try:
                _orig_setDriver(self, key, value, report, force, uom)
            except Exception:
                pass
        udi_interface.Node.setDriver = _mock_setDriver
        def _mock_reportCmd(self, cmd, value=None):
            if not hasattr(self, '_reported_cmds'):
                self._reported_cmds = []
            self._reported_cmds.append((cmd, value))
        udi_interface.Node.reportCmd = _mock_reportCmd
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
from profile_def import build_profile_definition, dynamic_profile_payload, PROFILE_VERSION


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
        self.last_update_time = 1728148800
        self.supports_local_access = True
        self.battery_type = 'ac_powerwall'

    # Getters
    def getTPW_onLine(self): return self.online
    def getTPW_lastUpdateTime(self, site_id=None):
        if not self.online:
            return None
        return self.last_update_time
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
    def getTPW_gridImportMode(self, site_id): return self.grid_import_mode
    def getTPW_gridExportMode(self, site_id): return self.grid_export_mode
    def getTPW_evChargeReserve(self, site_id): return self.ev_charge_reserve

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

    def getTPW_supports_local_access(self, site_id=None):
        return self.supports_local_access

    def getTPW_battery_type(self, site_id=None):
        return self.battery_type

    def cloud_authenticated(self):
        return True

    def init_cloud(self, region=None):
        return True

    def init_cloud_data(self, site_id):
        return True

    def tesla_get_products(self):
        return {'site_12345678': {'energy_site_id': '12345678', 'site_name': 'Power Wall Status'}}


# ---------------------------------------------------------------------------
# 3. Test Suites
# ---------------------------------------------------------------------------

class TestProfileXmlAndNls(unittest.TestCase):
    """Verifies profile XML standards and consistency with Python Node classes."""

    def setUp(self):
        profile_dir = None
        for candidate in ['profile.static', 'profile']:
            cand_path = os.path.join(ROOT_DIR, candidate)
            test_file = os.path.join(cand_path, 'editor', 'editors.xml')
            try:
                if os.path.exists(test_file):
                    with open(test_file, 'rb') as f:
                        f.read(10)
                    profile_dir = cand_path
                    break
            except (OSError, PermissionError):
                continue
        if not profile_dir:
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
        """Verifies editor IDs and range NLS attributes are uppercase, no underscores, and not reserved."""
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

            for r in editor.findall('range'):
                nls = r.attrib.get('nls')
                if nls is not None:
                    self.assertEqual(nls, nls.upper(), f"Range nls '{nls}' in editor '{eid}' is not all uppercase")
                    self.assertNotIn('_', nls, f"Range nls '{nls}' in editor '{eid}' contains underscore")
                    self.assertNotIn(nls, self.reserved_words, f"Range nls '{nls}' in editor '{eid}' is a reserved word")

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

            for cmd in nd.findall('.//cmd'):
                cid = cmd.attrib.get('id', '').strip()
                if cid:
                    self.assertEqual(cid, cid.upper(), f"Command ID '{cid}' is not uppercase")
                    self.assertNotIn('_', cid, f"Command ID '{cid}' in NodeDef '{nid}' contains underscore")

    def test_nls_keys_have_no_underscores(self):
        """Verifies that all NLS keys in en_us.txt contain no underscores."""
        with open(self.nls_txt, 'r', encoding='utf-8') as f:
            for line_no, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key = line.split('=', 1)[0].strip()
                    self.assertNotIn('_', key, f"en_us.txt line {line_no} key '{key}' contains underscore")

    def test_no_spaces_around_equals_in_profile_files(self):
        """Verifies that editors.xml, nodedefs.xml, and en_us.txt contain no spaces around '='."""
        for path in [self.editors_xml, self.nodedefs_xml, self.nls_txt]:
            with open(path, 'r', encoding='utf-8') as f:
                for line_no, line in enumerate(f, 1):
                    line = line.strip()
                    if '=' in line:
                        self.assertNotIn(' =', line, f"{os.path.basename(path)} line {line_no} contains space before '=': {line}")
                        self.assertNotIn('= ', line, f"{os.path.basename(path)} line {line_no} contains space after '=': {line}")

    def test_specific_driver_uoms(self):
        """Verifies specific critical driver UOMs match hardware definitions."""
        status_drivers = {d['driver']: d['uom'] for d in teslaPWStatusNode.drivers}
        self.assertEqual(status_drivers.get('GV8'), 33, "PWSTATUS GV8 must have UOM 33 (kWh)")
        self.assertEqual(status_drivers.get('ST'), 25, "PWSTATUS ST must have UOM 25")
        self.assertEqual(status_drivers.get('TIME'), 151, "PWSTATUS TIME must have UOM 151")

        ctrl_drivers = {d['driver']: d['uom'] for d in TeslaPWController.drivers}
        self.assertEqual(ctrl_drivers.get('GV3'), 55, "CONTROLLER GV3 must have UOM 55 (count)")

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

    def test_no_unused_editors_in_xml(self):
        """Verifies that every editor in editors.xml is referenced by at least one nodedef."""
        ed_tree = ET.parse(self.editors_xml)
        editor_ids = {e.attrib.get('id', '').strip() for e in ed_tree.getroot().findall('editor')}

        nd_tree = ET.parse(self.nodedefs_xml)
        used_ids = set()
        for st in nd_tree.getroot().findall('.//st'):
            ed = st.attrib.get('editor', '').strip()
            if ed:
                used_ids.add(ed)
        for p in nd_tree.getroot().findall('.//p'):
            ed = p.attrib.get('editor', '').strip()
            if ed:
                used_ids.add(ed)

        unused = editor_ids - used_ids
        self.assertFalse(unused, f"editors.xml contains unused editors: {unused}")

    def test_no_commented_lines_in_profile_files(self):
        """Verifies that editors.xml, nodedefs.xml, and en_us.txt do not contain commented-out lines."""
        with open(self.editors_xml, 'r', encoding='utf-8') as f:
            self.assertNotIn('<!--', f.read(), "editors.xml contains commented-out XML lines")
        with open(self.nodedefs_xml, 'r', encoding='utf-8') as f:
            self.assertNotIn('<!--', f.read(), "nodedefs.xml contains commented-out XML lines")
        with open(self.nls_txt, 'r', encoding='utf-8') as f:
            for line in f:
                self.assertFalse(line.strip().startswith('#'), f"en_us.txt contains commented line: {line.strip()}")

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
        self.assertIn('TIME', drivers)
        self.assertEqual(drivers['TIME']['value'], 1728148800)
        self.assertEqual(drivers['TIME']['uom'], 151)

    def test_time_only_updates_when_new_data_received(self):
        self.node.start()
        self.assertEqual(self.node._driver_values['TIME']['value'], 1728148800)

        # Clear recorded driver writes
        self.node._driver_values.clear()

        # Update with unchanged data timestamp
        self.node.updateISYdrivers()
        self.assertNotIn('TIME', self.node._driver_values, "TIME should not update when data timestamp is unchanged")

        # Now simulate new data received from Powerwall
        self.tpw.last_update_time = 1728148850
        self.node.updateISYdrivers()
        self.assertIn('TIME', self.node._driver_values)
        self.assertEqual(self.node._driver_values['TIME']['value'], 1728148850)

    def test_update_drivers_offline(self):
        self.tpw.online = False
        self.node.start()
        self.assertEqual(self.node._driver_values['ST']['value'], 0)
        self.assertNotIn('TIME', self.node._driver_values)

    def test_isy_update_command(self):
        self.node.start()
        self.node.ISYupdate({'cmd': 'UPDATE'})
        self.assertIn((self.site_id, 'all'), self.tpw.poll_calls)

    def test_tesla_timestamp_parsing(self):
        from TeslaInfoV2 import parse_tesla_timestamp, extract_meter_timestamp
        self.assertEqual(parse_tesla_timestamp(1728148800), 1728148800)
        self.assertEqual(parse_tesla_timestamp('1728148800'), 1728148800)
        ts_utc = parse_tesla_timestamp('2021-11-22T22:15:06Z')
        self.assertEqual(ts_utc, 1637619306)
        ts_offset = parse_tesla_timestamp('2021-11-22T22:15:06.590577619-07:00')
        self.assertEqual(ts_offset, 1637644506)

        class MockMeter:
            def __init__(self):
                self.last_communication_time = '2021-11-22T22:15:06.590577619-07:00'
        self.assertEqual(extract_meter_timestamp(MockMeter()), 1637644506)

    def test_tesla_info_local_last_update_time(self):
        from TeslaInfoV2 import tesla_info
        tpw = tesla_info(None)
        tpw.localAccessUp = True
        tpw.firstPollCompleted = True

        class MockMeter:
            def __init__(self, t):
                self.last_communication_time = t
        tpw.siteMeter = MockMeter('2021-11-22T22:15:06.590577619-07:00')
        tpw.batteryMeter = MockMeter('2021-11-22T22:15:07.123456-07:00')

        self.assertEqual(tpw.getTPW_lastUpdateTime(), 1637644507)


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
        self.assertEqual(self.node._driver_values['ST']['value'], 1)      # Op mode
        self.assertEqual(self.node._driver_values['GV1']['value'], 20.0)  # Backup %
        self.assertEqual(self.node._driver_values['GV3']['value'], 0)     # Storm mode
        self.assertEqual(self.node._driver_values['GV5']['value'], 0)     # Grid import mode
        self.assertEqual(self.node._driver_values['GV6']['value'], 0)     # Grid export mode
        self.assertEqual(self.node._driver_values['GV7']['value'], 50)    # EV reserve %

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
        self.assertEqual(self.node._driver_values['ST']['value'], 2)

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

    def test_setup_node_command_mappings_both_formats(self):
        """Verifies commands dictionary maps both new clean IDs and old underscore IDs."""
        self.assertIn('BACKUPPCT', self.node.commands)
        self.assertIn('BACKUP_PCT', self.node.commands)
        self.assertIn('OPMODE', self.node.commands)
        self.assertIn('OP_MODE', self.node.commands)
        self.assertIn('STORMMODE', self.node.commands)
        self.assertIn('STORM_MODE', self.node.commands)
        self.assertIn('GRIDMODE', self.node.commands)
        self.assertIn('GRID_MODE', self.node.commands)
        self.assertIn('EVCHRGMODE', self.node.commands)
        self.assertIn('EV_CHRG_MODE', self.node.commands)


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

        # Today
        self.assertEqual(drivers['ST']['value'], 14.50)
        self.assertEqual(drivers['GV0']['value'], 1)
        self.assertEqual(drivers['GV8']['value'], 14.50)
        self.assertNotIn('GV1', drivers)
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
    """Verifies PG3x / IoX Dynamic JSON profile definition in code and node server integration.
    
    Mirrors the testing standards from udi-kidde (test_profile_schema.py) and udi-nuheatv2.
    """

    def setUp(self):
        self.payload = build_profile_definition(generator_installed=True)
        self.editors = self.payload['editors']
        self.editor_map = {e['id']: e for e in self.editors}
        self.nodedefs = self.payload['nodedefs']
        self.nodedef_map = {n['id']: n for n in self.nodedefs}
        self.reserved_words = {'CON', 'TIME', 'BOOL'}

    def test_profile_payload_structure(self):
        """Verifies top-level dynamic JSON profile structure, version, and wildcard deletes."""
        self.assertEqual(self.payload.get('version'), PROFILE_VERSION)
        self.assertIn('delete', self.payload)
        self.assertEqual(self.payload['delete'].get('editors'), ['*'])
        self.assertEqual(self.payload['delete'].get('nodedefs'), ['*'])
        self.assertEqual(len(self.editors), 20)
        self.assertEqual(len(self.nodedefs), 4)
        self.assertIn('nls', self.payload)
        self.assertIsInstance(self.payload['nls'], dict)
        self.assertGreater(len(self.payload['nls']), 100)
        for k in self.payload['nls']:
            self.assertNotIn('_', k, f"Dynamic NLS key '{k}' contains underscore")

    def test_no_unused_editors(self):
        """Verifies that every editor in the dynamic profile is actively referenced by a property or command parameter."""
        used_editors = set()
        for nd in self.nodedefs:
            for prop in nd.get('properties', []):
                used_editors.add(prop['editor'])
            for cmd in nd.get('cmds', {}).get('accepts', []):
                for param in cmd.get('parameters', []):
                    used_editors.add(param['editor'])
        defined_editors = {e['id'] for e in self.editors}
        unused = defined_editors - used_editors
        self.assertFalse(unused, f"Dynamic profile contains unused editors: {unused}")

    def test_dynamic_editors_standards(self):
        """Verifies dynamic JSON editors comply with PG3x conventions (uppercase, no underscore, no reserved words, inline names for UOM 25)."""
        seen = set()
        for ed in self.editors:
            eid = ed.get('id', '')
            self.assertTrue(eid, "Editor missing id")
            self.assertNotIn(eid, seen, f"Duplicate editor ID: {eid}")
            seen.add(eid)
            self.assertEqual(eid, eid.upper(), f"Editor ID '{eid}' is not uppercase")
            self.assertNotIn('_', eid, f"Editor ID '{eid}' contains underscore")
            self.assertNotIn(eid, self.reserved_words, f"Editor ID '{eid}' is reserved word")

            ranges = ed.get('ranges', [])
            self.assertTrue(isinstance(ranges, list) and len(ranges) > 0, f"Editor '{eid}' missing ranges list")
            for r in ranges:
                subset = r.get('subset')
                if subset is not None:
                    self.assertNotIn('-', str(subset), f"Editor '{eid}' subset has range hyphen: '{subset}'")
                    parts = [p.strip() for p in str(subset).split(',')]
                    for p in parts:
                        self.assertTrue(p.isdigit(), f"Editor '{eid}' non-integer subset value: '{p}'")

                # UOM 25 ranges MUST have inline names dictionary and nls attribute for mapped text display
                if str(r.get('uom')) == '25':
                    names = r.get('names')
                    self.assertIsInstance(names, dict, f"Editor '{eid}' UOM 25 range missing names dict")
                    self.assertTrue(len(names) > 0, f"Editor '{eid}' UOM 25 range names dict is empty")
                    for k, v in names.items():
                        self.assertTrue(str(k).isdigit(), f"Editor '{eid}' name key '{k}' must be integer value")
                        self.assertTrue(isinstance(v, str) and len(v.strip()) > 0, f"Editor '{eid}' name value for '{k}' must be non-empty string")

                    r_nls = r.get('nls')
                    self.assertIsNotNone(r_nls, f"Editor '{eid}' UOM 25 range missing 'nls' attribute")
                    self.assertEqual(r_nls, r_nls.upper(), f"Editor '{eid}' range nls '{r_nls}' is not uppercase")
                    self.assertNotIn('_', r_nls, f"Editor '{eid}' range nls '{r_nls}' contains underscore")

    def test_dynamic_nodedefs_standards(self):
        """Verifies dynamic JSON nodedefs reference valid editors, commands, and follow naming rules."""
        seen = set()
        for nd in self.nodedefs:
            nid = nd.get('id', '')
            self.assertTrue(nid, "NodeDef missing id")
            self.assertNotIn(nid, seen, f"Duplicate nodeDef ID: {nid}")
            seen.add(nid)
            self.assertEqual(nid, nid.upper(), f"NodeDef ID '{nid}' is not uppercase")
            self.assertNotIn('_', nid, f"NodeDef ID '{nid}' contains underscore")
            self.assertNotIn(nid, self.reserved_words, f"NodeDef ID '{nid}' is reserved word")
            self.assertTrue(nd.get('name'), f"NodeDef '{nid}' missing human-readable name")
            self.assertTrue(nd.get('icon'), f"NodeDef '{nid}' missing icon")

            # Properties validation
            for prop in nd.get('properties', []):
                pid = prop.get('id')
                pname = prop.get('name')
                ed_ref = prop.get('editor')
                self.assertTrue(pid, f"NodeDef '{nid}' property missing id")
                self.assertTrue(pname, f"NodeDef '{nid}' property '{pid}' missing name")
                self.assertIn(ed_ref, self.editor_map, f"NodeDef '{nid}' property '{pid}' references missing editor '{ed_ref}'")

            # Commands validation
            cmds = nd.get('cmds', {})
            for cmd in cmds.get('accepts', []):
                cid = cmd.get('id')
                cname = cmd.get('name')
                self.assertTrue(cid, f"NodeDef '{nid}' accept cmd missing id")
                self.assertEqual(cid, cid.upper(), f"NodeDef '{nid}' cmd '{cid}' is not uppercase")
                self.assertNotIn('_', cid, f"NodeDef '{nid}' cmd '{cid}' contains underscore")
                self.assertTrue(cname, f"NodeDef '{nid}' accept cmd '{cid}' missing name")
                for p in cmd.get('parameters', []):
                    ped_ref = p.get('editor')
                    self.assertIn(ped_ref, self.editor_map, f"NodeDef '{nid}' param references missing editor '{ped_ref}'")

            # UDI Release requirement: commands under 'sends' (DON, DOF) must not have 'name' attribute
            for cmd in cmds.get('sends', []):
                cid = cmd.get('id')
                self.assertIn(cid, ('DON', 'DOF'), f"Unexpected command '{cid}' in sends")
                self.assertNotIn('name', cmd, f"NodeDef '{nid}' sends command '{cid}' must not have a 'name' attribute")

    def test_driver_uom_consistency_with_dynamic_profile(self):
        """Verifies Python Node class driver UOMs match their dynamic profile editor range UOMs."""
        node_classes = {
            'CONTROLLER': TeslaPWController,
            'PWSTATUS': teslaPWStatusNode,
            'PWHISTORY': teslaPWHistoryNode,
            'PWSETUP': teslaPWSetupNode,
        }

        for nid, cls in node_classes.items():
            nd = self.nodedef_map[nid]
            nd_props = {p['id']: p['editor'] for p in nd.get('properties', [])}
            py_drivers = {d['driver']: str(d.get('uom', '')) for d in getattr(cls, 'drivers', [])}

            for drv, py_uom in py_drivers.items():
                ed_id = nd_props.get(drv)
                self.assertIsNotNone(ed_id, f"Node {nid} driver '{drv}' not found in dynamic profile properties")
                editor = self.editor_map[ed_id]
                allowed_uoms = [str(r.get('uom')) for r in editor.get('ranges', [])]
                self.assertIn(
                    py_uom,
                    allowed_uoms,
                    f"{nid} driver '{drv}' has uom={py_uom} in Python, but dynamic editor '{ed_id}' only allows uoms={allowed_uoms}"
                )

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
        self.assertEqual(poly._ifaceData.profile_version, PROFILE_VERSION)

        # Second call (idempotent): should NOT re-send because version is identical
        controller.update_dynamic_profile()
        self.assertEqual(len(poly.json_profile_updates), 1)

        # Forced update: sends updateJsonProfile even when version matches
        controller.update_dynamic_profile(force=True)
        self.assertEqual(len(poly.json_profile_updates), 2)

    def test_controller_profiles_match_method(self):
        """Tests controller._profiles_match helper method."""
        poly = MockPolyglotInterface()
        mock_cloud = types.SimpleNamespace(
            customDataHandlerDone=True,
            customNsHandler=lambda *a: None,
            oauthHandler=lambda *a: None
        )
        controller = TeslaPWController(poly, 'controller', 'controller', 'Tesla PowerWall Info', mock_cloud)
        p1 = build_profile_definition()
        p2 = build_profile_definition()
        self.assertTrue(controller._profiles_match(p1, p2))
        self.assertFalse(controller._profiles_match(p1, {}))
        self.assertFalse(controller._profiles_match(None, p2))

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


class TestStartupSequence(unittest.TestCase):
    """Verifies startup sequence, error fixes, parameter sanitization, and authentication notice behavior."""

    def test_tesla_oauth_custom_data_handler_no_error(self):
        """Verifies customDataHandler does not raise AttributeError and sets customDataHandlerDone."""
        from TeslaOauth import teslaAccess
        poly = MockPolyglotInterface()
        oauth = teslaAccess(poly, 'energy_device_data')
        oauth.customDataHandler({'some': 'data'})
        self.assertTrue(oauth.customDataHandlerDone)

    def test_tesla_oauth_custom_ns_handler_oauth(self):
        """Verifies customNsHandler with key='oauth' sets customNsHandlerDone and customNsDone."""
        from TeslaOauth import teslaAccess
        poly = MockPolyglotInterface()
        oauth = teslaAccess(poly, 'energy_device_data')
        oauth.customNsHandler('oauth', {'client_id': 'xyz'})
        self.assertTrue(oauth.customNsHandlerDone)
        self.assertTrue(oauth.customNsDone())

    def test_tesla_oauth_custom_ns_handler_oauth_tokens(self):
        """Verifies customNsHandler with key='oauthTokens' sets customNsHandlerDone and customNsDone."""
        from TeslaOauth import teslaAccess
        poly = MockPolyglotInterface()
        oauth = teslaAccess(poly, 'energy_device_data')
        oauth.customNsHandler('oauthTokens', {'access_token': 'abc', 'expiry': '2099-01-01'})
        self.assertTrue(oauth.customNsHandlerDone)
        self.assertTrue(oauth.customNsDone())

    def test_controller_config_done_handler_unblocks_startup(self):
        """Verifies configDoneHandler sets config_done, customParam_done, and TPW_cloud flags."""
        from TeslaOauth import teslaAccess
        poly = MockPolyglotInterface()
        oauth = teslaAccess(poly, 'energy_device_data')
        controller = TeslaPWController(poly, 'controller', 'controller', 'Tesla PowerWall Info', oauth)
        self.assertFalse(controller.config_done)
        controller.configDoneHandler()
        self.assertTrue(controller.config_done)
        self.assertTrue(controller.customParam_done)
        self.assertTrue(oauth.customNsHandlerDone)

    def test_custom_params_sanitizes_ip_and_region(self):
        """Verifies customParamsHandler sanitizes comma in IP address and valid regions."""
        from TeslaOauth import teslaAccess
        poly = MockPolyglotInterface()
        oauth = teslaAccess(poly, 'energy_device_data')
        controller = TeslaPWController(poly, 'controller', 'controller', 'Tesla PowerWall Info', oauth)
        user_params = {
            'LOCAL_IP_ADDRESS': '192,168.1.151',
            'region': 'NA',
            'cloud_access_en': 'True',
            'local_access_en': 'True'
        }
        controller.customParamsHandler(user_params)
        self.assertEqual(controller.LOCAL_IP_ADDRESS, '192.168.1.151')
        self.assertEqual(controller.region, 'NA')
        self.assertTrue(controller.cloud_access_enabled)

    def test_unauthenticated_notice_displayed_and_cleared_on_auth(self):
        """Verifies notice is posted when unauthenticated and removed once authenticated."""
        from TeslaOauth import teslaAccess
        poly = MockPolyglotInterface()
        oauth = teslaAccess(poly, 'energy_device_data')
        controller = TeslaPWController(poly, 'controller', 'controller', 'Tesla PowerWall Info', oauth)
        
        # User enables cloud access but has not authenticated yet
        controller.customParamsHandler({'cloud_access_en': 'True', 'region': 'NA'})
        controller.configDoneHandler()
        
        # Notice must be present directing the user to authenticate
        self.assertIn('auth', poly.Notices)
        self.assertEqual(poly.Notices['auth'], 'Please initiate authentication - press Authenticate button')
        
        # Now simulate user authenticating via OAuth callback
        controller.oauthHandler({'access_token': 'valid_token', 'refresh_token': 'ref_tok', 'expires_in': 3600})
        
        # Notice must be cleared
        self.assertNotIn('auth', poly.Notices)

    def test_oauth_tokens_restored_from_db_clears_auth_notice(self):
        """Verifies that when stored tokens arrive from PG3 via customNsHandler, any existing auth notice is cleared."""
        from TeslaOauth import teslaAccess
        poly = MockPolyglotInterface()
        oauth = teslaAccess(poly, 'energy_device_data')
        controller = TeslaPWController(poly, 'controller', 'controller', 'Tesla PowerWall Info', oauth)

        # Startup triggers configDone before tokens arrive -> notice posted
        controller.customParamsHandler({'cloud_access_en': 'True', 'region': 'NA'})
        controller.configDoneHandler()
        self.assertIn('auth', poly.Notices)

        # PG3 delivers stored tokens from database
        oauth.customNsHandler('oauthTokens', {'access_token': 'restored_token', 'refresh_token': 'ref_123', 'expires_in': 28800})
        
        # Stored tokens must clear the notice and authenticated() must be True
        self.assertNotIn('auth', poly.Notices)
        self.assertTrue(oauth.authenticated())

    def test_authenticated_handles_missing_expiry(self):
        """Verifies authenticated() handles token dictionary lacking 'expiry' without error or false negative."""
        from TeslaOauth import teslaAccess
        poly = MockPolyglotInterface()
        oauth = teslaAccess(poly, 'energy_device_data')
        
        # Load raw tokens with expires_in but no expiry
        oauth.customNsHandler('oauthTokens', {'access_token': 'my_token', 'refresh_token': 'ref', 'expires_in': 28800})
        self.assertTrue(oauth.authenticated())
        self.assertIn('expiry', oauth._oauthTokens)

    def test_custom_params_updates_client_secret(self):
        """Verifies customParamsHandler applies client_secret or clientSecret to oauth settings."""
        from TeslaOauth import teslaAccess
        poly = MockPolyglotInterface()
        oauth = teslaAccess(poly, 'energy_device_data')
        controller = TeslaPWController(poly, 'controller', 'controller', 'Tesla PowerWall Info', oauth)

        controller.customParamsHandler({'client_secret': 'super_secret_123'})
        settings = oauth.getOauthSettings()
        self.assertEqual(settings.get('client_secret'), 'super_secret_123')

    def test_default_startup_cloud_only_no_local_placeholders(self):
        """Verifies default startup has cloud_access_enabled=True, local_access_enabled=False, and no placeholder injections."""
        from TeslaOauth import teslaAccess
        poly = MockPolyglotInterface()
        oauth = teslaAccess(poly, 'energy_device_data')
        controller = TeslaPWController(poly, 'controller', 'controller', 'Tesla PowerWall Info', oauth)

        controller.customParamsHandler({})
        self.assertTrue(controller.cloud_access_enabled)
        self.assertFalse(controller.local_access_enabled)
        self.assertIsNone(controller.LOCAL_IP_ADDRESS)
        self.assertIsNone(controller.region)
        self.assertNotIn('region', poly.Notices)
        self.assertNotIn('LOCAL_IP_ADDRESS', controller.customParameters)
        self.assertNotIn('LOCAL_EMAIL', controller.customParameters)

    def test_auto_discover_user_region(self):
        """Verifies discover_user_region queries /users/region and updates endpoint & region."""
        from TeslaOauth import teslaAccess
        poly = MockPolyglotInterface()
        oauth = teslaAccess(poly, 'energy_device_data')

        oauth._callApi = lambda method, url: {
            'response': {
                'region': 'eu',
                'fleet_api_base_url': 'https://fleet-api.prd.eu.vn.cloud.tesla.com'
            }
        }
        res = oauth.discover_user_region()
        self.assertEqual(res, 'EU')
        self.assertEqual(oauth.region, 'EU')
        self.assertEqual(oauth.yourApiEndpoint, 'https://fleet-api.prd.eu.vn.cloud.tesla.com/api/1')

    def test_tesla_pwoauth_supports_local_access_detection(self):
        """Verifies tesla_supports_local_access detects Powerwall 2 vs Powerwall 3 accurately."""
        from TeslaPWOauth import teslaPWAccess
        poly = MockPolyglotInterface()
        tpw = teslaPWAccess(poly, 'energy_device_data')

        # Powerwall 2 (ac_powerwall + teg)
        tpw.site_info['site_pw2'] = {
            'components': {'battery_type': 'ac_powerwall', 'gateway_type': 'teg', 'battery': True}
        }
        self.assertEqual(tpw.tesla_battery_type('site_pw2'), 'ac_powerwall')
        self.assertEqual(tpw.tesla_gateway_type('site_pw2'), 'teg')
        self.assertTrue(tpw.tesla_supports_local_access('site_pw2'))

        # Powerwall 2 (powerwall2 name + gateway2)
        tpw.site_info['site_pw2_alt'] = {
            'battery_type': 'powerwall2',
            'gateway_type': 'gateway2',
            'components': {'battery': True}
        }
        self.assertEqual(tpw.tesla_battery_type('site_pw2_alt'), 'powerwall2')
        self.assertEqual(tpw.tesla_gateway_type('site_pw2_alt'), 'gateway2')
        self.assertTrue(tpw.tesla_supports_local_access('site_pw2_alt'))

        # Powerwall 3 (powerwall3 + pw3)
        tpw.site_info['site_pw3'] = {
            'components': {'battery_type': 'powerwall3', 'gateway_type': 'pw3', 'battery': True}
        }
        self.assertEqual(tpw.tesla_battery_type('site_pw3'), 'powerwall3')
        self.assertEqual(tpw.tesla_gateway_type('site_pw3'), 'pw3')
        self.assertFalse(tpw.tesla_supports_local_access('site_pw3'))

        # Powerwall 3 variant with neop gateway
        tpw.site_info['site_neop'] = {
            'components': {'gateway_type': 'neop', 'battery': True}
        }
        self.assertFalse(tpw.tesla_supports_local_access('site_neop'))

        # Non-battery site / empty info
        tpw.site_info['site_solar_only'] = {'components': {'solar': True}}
        self.assertFalse(tpw.tesla_supports_local_access('site_solar_only'))
        self.assertFalse(tpw.tesla_supports_local_access('nonexistent_site'))

    def test_tesla_info_supports_local_access_delegation(self):
        """Verifies tesla_info wrappers delegate to TPWcloud and handle errors safely."""
        from TeslaInfoV2 import tesla_info
        tpw = tesla_info(None)

        class MockCloud:
            def tesla_supports_local_access(self, site_id):
                return site_id == 'pw2'
            def tesla_battery_type(self, site_id):
                return 'ac_powerwall' if site_id == 'pw2' else 'powerwall3'

        tpw.TPWcloud = MockCloud()
        self.assertTrue(tpw.getTPW_supports_local_access('pw2'))
        self.assertFalse(tpw.getTPW_supports_local_access('pw3'))
        self.assertEqual(tpw.getTPW_battery_type('pw2'), 'ac_powerwall')
        self.assertEqual(tpw.getTPW_battery_type('pw3'), 'powerwall3')

        # None / missing method error safety
        tpw.TPWcloud = None
        self.assertFalse(tpw.getTPW_supports_local_access('pw2'))
        self.assertEqual(tpw.getTPW_battery_type('pw2'), '')

    def test_controller_start_pw2_presents_local_params_and_notice(self):
        """Verifies controller start() detects PW2 and dynamically presents local params and notice."""
        from TeslaOauth import teslaAccess
        poly = MockPolyglotInterface()
        oauth = teslaAccess(poly, 'energy_device_data')
        oauth.customNsHandlerDone = True
        controller = TeslaPWController(poly, 'controller', 'controller', 'Tesla PowerWall Info', oauth)

        mock_svc = MockTeslaService()
        mock_svc.supports_local_access = True
        mock_svc.battery_type = 'ac_powerwall'

        controller.TPW = mock_svc
        controller.config_done = True
        controller.customParam_done = True
        controller.nodes_in_db = []
        controller.region = 'NA'
        controller.LOCAL_IP_ADDRESS = None
        controller.customParameters = {}

        controller.start()

        self.assertIn('LOCAL_IP_ADDRESS', controller.customParameters)
        self.assertIn('LOCAL_USER_EMAIL', controller.customParameters)
        self.assertIn('LOCAL_USER_PASSWORD', controller.customParameters)
        self.assertEqual(controller.customParameters['LOCAL_IP_ADDRESS'], '')
        self.assertIn('local_opt', poly.Notices)
        self.assertIn('Powerwall 2 detected with local API support', poly.Notices['local_opt'])

    def test_controller_start_pw3_suppresses_local_params_and_clears_notice(self):
        """Verifies controller start() detects PW3, suppresses local params, and removes local_opt notice."""
        from TeslaOauth import teslaAccess
        poly = MockPolyglotInterface()
        oauth = teslaAccess(poly, 'energy_device_data')
        oauth.customNsHandlerDone = True
        controller = TeslaPWController(poly, 'controller', 'controller', 'Tesla PowerWall Info', oauth)

        mock_svc = MockTeslaService()
        mock_svc.supports_local_access = False
        mock_svc.battery_type = 'powerwall3'

        controller.TPW = mock_svc
        controller.config_done = True
        controller.customParam_done = True
        controller.nodes_in_db = []
        controller.region = 'NA'
        controller.LOCAL_IP_ADDRESS = None
        controller.customParameters = {}
        poly.Notices['local_opt'] = 'previous notice'

        controller.start()

        self.assertNotIn('LOCAL_IP_ADDRESS', controller.customParameters)
        self.assertNotIn('LOCAL_USER_EMAIL', controller.customParameters)
        self.assertNotIn('LOCAL_USER_PASSWORD', controller.customParameters)
        self.assertNotIn('local_opt', poly.Notices)

    def test_controller_start_configured_local_ip_clears_notice(self):
        """Verifies that when LOCAL_IP_ADDRESS is already configured, local_opt notice is deleted."""
        from TeslaOauth import teslaAccess
        poly = MockPolyglotInterface()
        oauth = teslaAccess(poly, 'energy_device_data')
        oauth.customNsHandlerDone = True
        controller = TeslaPWController(poly, 'controller', 'controller', 'Tesla PowerWall Info', oauth)

        mock_svc = MockTeslaService()
        mock_svc.supports_local_access = True
        mock_svc.battery_type = 'ac_powerwall'

        controller.TPW = mock_svc
        controller.config_done = True
        controller.customParam_done = True
        controller.nodes_in_db = []
        controller.region = 'NA'
        controller.LOCAL_IP_ADDRESS = '192.168.1.150'
        controller.customParameters = {'LOCAL_IP_ADDRESS': '192.168.1.150'}
        poly.Notices['local_opt'] = 'old notice'

        controller.start()

        self.assertEqual(controller.customParameters['LOCAL_IP_ADDRESS'], '192.168.1.150')
        self.assertNotIn('local_opt', poly.Notices)



class TestPhase1BugFixes(unittest.TestCase):
    """Verifies critical bug fixes implemented in Phase 1."""

    def test_tesla_local_login_failure_graceful(self):
        """Verifies local login failures do not invoke os.exit() and return False gracefully."""
        from TeslaLocal import tesla_local
        local = tesla_local('user@example.com', 'password', '192.168.1.100')
        class MockFailedPowerwall:
            def login(self, pwd, email):
                pass
            def is_authenticated(self):
                return False
        local.PWlocal = MockFailedPowerwall()
        import TeslaLocal
        orig_pw = TeslaLocal.Powerwall
        TeslaLocal.Powerwall = lambda ip: MockFailedPowerwall()
        try:
            res = local.loginLocal()
            self.assertFalse(res)
            self.assertFalse(local.localAccessUp)
        finally:
            TeslaLocal.Powerwall = orig_pw

    def test_grid_export_mode_mapping(self):
        """Verifies tesla_set_grid_import_export properly maps integer indices and bools."""
        from TeslaPWOauth import teslaPWAccess
        poly = MockPolyglotInterface()
        tpw = teslaPWAccess(poly, 'energy_device_data')
        calls = []
        tpw._callApi = lambda method, url, body=None: calls.append((method, url, body))

        # Test integer 0 -> pv_only, solar_charge=1 (enabled) -> disallow=False
        tpw.tesla_set_grid_import_export('site_123', False, 0)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], 'POST')
        self.assertEqual(calls[0][1], '/energy_sites/site_123/grid_import_export')
        self.assertEqual(calls[0][2], {
            'disallow_charge_from_grid_with_solar_installed': False,
            'customer_preferred_export_rule': 'pv_only'
        })

        # Test integer 1 -> battery_ok
        tpw.tesla_set_grid_import_export('site_123', True, 1)
        self.assertEqual(calls[1][2], {
            'disallow_charge_from_grid_with_solar_installed': True,
            'customer_preferred_export_rule': 'battery_ok'
        })

        # Test integer 2 -> never
        tpw.tesla_set_grid_import_export('site_123', False, 2)
        self.assertEqual(calls[2][2], {
            'disallow_charge_from_grid_with_solar_installed': False,
            'customer_preferred_export_rule': 'never'
        })

    def test_tesla_pwoauth_data_integrity(self):
        """Verifies total_pack_energy does not crash with double index and dictionary is not overwritten."""
        from TeslaPWOauth import teslaPWAccess
        poly = MockPolyglotInterface()
        tpw = teslaPWAccess(poly, 'energy_device_data')
        
        tpw.site_live_info['site_123'] = {
            'total_pack_energy': 13500,
            'energy_left': 11000,
            'percentage_charged': 81.5
        }
        # Verify tesla_total_battery returns correct scalar without KeyError
        self.assertEqual(tpw.tesla_total_battery('site_123'), 13500)

        # Verify teslaExtractEnergyRemaining does NOT mutate self.total_pack_energy from dict to scalar
        rem = tpw.teslaExtractEnergyRemaining('site_123')
        self.assertEqual(rem, 11000)
        self.assertIsInstance(tpw.total_pack_energy, dict)
        self.assertEqual(tpw.total_pack_energy['site_123'], 13500)

    def test_tesla_extract_grid_and_ev_settings(self):
        """Verifies extracting grid import/export mode and EV reserve from site_info."""
        from TeslaPWOauth import teslaPWAccess
        poly = MockPolyglotInterface()
        tpw = teslaPWAccess(poly, 'energy_device_data')

        tpw.site_info['site_123'] = {
            'disallow_charge_from_grid_with_solar_installed': False,
            'customer_preferred_export_rule': 'battery_ok',
            'off_grid_vehicle_charging_reserve_percent': 65
        }
        self.assertEqual(tpw.teslaExtractGridImportMode('site_123'), 1)
        self.assertEqual(tpw.teslaExtractGridExportMode('site_123'), 1)
        self.assertEqual(tpw.teslaExtractEvChargeReserve('site_123'), 65)

        tpw.site_info['site_123']['disallow_charge_from_grid_with_solar_installed'] = True
        tpw.site_info['site_123']['customer_preferred_export_rule'] = 'pv_only'
        self.assertEqual(tpw.teslaExtractGridImportMode('site_123'), 0)
        self.assertEqual(tpw.teslaExtractGridExportMode('site_123'), 0)


class TestPhase2BugFixes(unittest.TestCase):
    """Verifies math, polling optimization, and caching bug fixes implemented in Phase 2."""

    def test_shortpoll_does_not_call_calendar_history(self):
        """Verifies shortPoll ('critical') queries live status but does NOT fetch calendar_history."""
        from TeslaPWOauth import teslaPWAccess
        poly = MockPolyglotInterface()
        tpw = teslaPWAccess(poly, 'energy_device_data')
        
        history_calls = []
        tpw.tesla_get_today_history = lambda site_id, kind: history_calls.append((site_id, kind))
        tpw.tesla_get_live_status = lambda site_id: {'energy_left': 12000}
        
        access = tpw.teslaUpdateCloudData('site_123', 'critical')
        self.assertTrue(access)
        self.assertEqual(len(history_calls), 0)

    def test_yesterday_caching_and_typo_fixed(self):
        """Verifies that yesterday's data does not re-fetch when already cached (typo yesteday fixed)."""
        from datetime import datetime
        from TeslaPWOauth import teslaPWAccess
        poly = MockPolyglotInterface()
        tpw = teslaPWAccess(poly, 'energy_device_data')
        
        tpw.previous_date_str = datetime.now().strftime('%Y-%m-%d')
        tpw.date_changed = False
        tpw.history_data['site_123'] = {
            'energy': {
                'yesterday': {
                    'consumer_energy_imported_from_battery': 1500
                }
            }
        }
        tpw.tesla_get_live_status = lambda site_id: {}
        tpw.tesla_get_site_info = lambda site_id: {}
        tpw.tesla_get_today_history = lambda site_id, kind: None
        
        yesterday_calls = []
        tpw.tesla_get_yesterday_history = lambda site_id, kind: yesterday_calls.append((site_id, kind))
        
        tpw.teslaUpdateCloudData('site_123', 'all')
        self.assertEqual(len(yesterday_calls), 0)

    def test_local_battery_import_and_yesterday_import_return_values(self):
        """Verifies getTPW_daysBattery_import and getTPW_yesterdayBattery_import return values, not None."""
        from TeslaInfoV2 import tesla_info
        tpw_cloud = types.SimpleNamespace()
        info = tesla_info(tpw_cloud)
        info.localAccessUp = True
        info.firstPollCompleted = True
        
        info.batteryMeter = types.SimpleNamespace(energy_imported=15000)
        info.DSbatteryMeter = types.SimpleNamespace(energy_imported=10000)
        
        val = info.getTPW_daysBattery_import('local')
        self.assertEqual(val, 5.0)

        info.yesterdayTotalBattery_imp = 6200
        y_val = info.getTPW_yesterdayBattery_import('local')
        self.assertEqual(y_val, 6.2)

    def test_midnight_rollover_logic(self):
        """Verifies midnight rollover updates lastDay and preserves daysTotalGrid in yesterdayTotalGrid."""
        from datetime import date, timedelta
        from TeslaInfoV2 import tesla_info
        tpw_cloud = types.SimpleNamespace()
        tpw_cloud.teslaUpdateCloudData = lambda s, m: True
        info = tesla_info(tpw_cloud)
        
        info.lastDay = date.today() - timedelta(days=1)
        info.daysTotalGrid = 15.5
        info.daysTotalGridServices = 2.0
        info.daysTotalSolar = 20.0
        info.daysTotalConsumption = 18.0
        info.daysTotalGeneraton = 5.0
        info.daysTotalBattery = 4.0
        info.daysTotalBattery_imp = 3.0
        info.daysTotalBattery_exp = 7.0
        info.daysTotalGenerator = 0.0
        info.daysTotalSite_imp = 12.0
        
        info.pollSystemData('site_123', 'critical')
        
        self.assertEqual(info.lastDay, date.today())
        self.assertEqual(info.yesterdayTotalGrid, 15.5)
        self.assertEqual(info.yesterdayTotalGridServices, 2.0)


class TestPhase3BugFixes(unittest.TestCase):
    """Verifies Phase 3 Fleet API modernization, network hardening, timeouts, and error handling."""

    def test_oauth_scope_string_uses_openid(self):
        """Verifies that TeslaPW2main and POLYGLOT_CONFIG specify 'openid' instead of 'open_id'."""
        with open(os.path.join(ROOT_DIR, 'TeslaPW2main.py'), 'r') as f:
            content = f.read()
        self.assertIn("'energy_device_data energy_cmds openid offline_access'", content)
        self.assertNotIn("open_id", content)

    def test_cloud_set_region_fleet_token_endpoint(self):
        """Verifies cloud_set_region updates token_endpoint to the Fleet API endpoint."""
        from TeslaOauth import teslaAccess
        poly = MockPolyglotInterface()
        oauth = teslaAccess(poly, 'energy_device_data energy_cmds openid offline_access')
        oauth.cloud_set_region('NA')
        settings = oauth.getOauthSettings()
        self.assertEqual(settings.get('token_endpoint'), 'https://fleet-auth.prd.vn.cloud.tesla.com/oauth2/v3/token')
        self.assertEqual(settings.get('auth_endpoint'), 'https://auth.tesla.com/oauth2/v3/authorize')
        self.assertIn('openid', settings.get('scope', ''))

    def test_session_pooling_and_timeout_parameters(self):
        """Verifies _callApi uses session with connect/read timeout."""
        from TeslaOauth import teslaAccess
        poly = MockPolyglotInterface()
        oauth = teslaAccess(poly, 'energy_device_data')
        self.assertTrue(hasattr(oauth, '_session'))
        self.assertEqual(oauth.timeout, (5.0, 15.0))

        oauth.getAccessToken = lambda: 'test_token'
        recorded_calls = []

        class MockSession:
            def get(self, url, headers=None, json=None, timeout=None):
                recorded_calls.append(('GET', url, headers, json, timeout))
                return types.SimpleNamespace(raise_for_status=lambda: None, json=lambda: {'result': 'ok'})

        oauth._session = MockSession()
        res = oauth._callApi('GET', '/products')
        self.assertEqual(res, {'result': 'ok'})
        self.assertEqual(len(recorded_calls), 1)
        method, url, headers, body, timeout = recorded_calls[0]
        self.assertEqual(method, 'GET')
        self.assertEqual(timeout, (5.0, 15.0))
        self.assertEqual(headers.get('Authorization'), 'Bearer test_token')

    def test_call_api_429_rate_limit_handling(self):
        """Verifies _callApi handles 429 rate limit with notice and warning without exception."""
        from TeslaOauth import teslaAccess
        poly = MockPolyglotInterface()
        oauth = teslaAccess(poly, 'energy_device_data')
        oauth.getAccessToken = lambda: 'test_token'

        import requests
        resp = types.SimpleNamespace(status_code=429, headers={'Retry-After': '60'})
        err = requests.exceptions.HTTPError('429 Client Error', response=resp)

        class MockSession:
            def get(self, url, **kwargs):
                raise err

        oauth._session = MockSession()
        res = oauth._callApi('GET', '/products')
        self.assertIsNone(res)
        self.assertIn('rate_limit', poly.Notices)
        self.assertIn('60', poly.Notices['rate_limit'])

    def test_call_api_412_precondition_failed_handling(self):
        """Verifies _callApi handles 412 Precondition Failed with region notice without exception."""
        from TeslaOauth import teslaAccess
        poly = MockPolyglotInterface()
        oauth = teslaAccess(poly, 'energy_device_data')
        oauth.region = 'NA'
        oauth.getAccessToken = lambda: 'test_token'

        import requests
        resp = types.SimpleNamespace(status_code=412, headers={})
        err = requests.exceptions.HTTPError('412 Precondition Failed', response=resp)

        class MockSession:
            def get(self, url, **kwargs):
                raise err

        oauth._session = MockSession()
        res = oauth._callApi('GET', '/products')
        self.assertIsNone(res)
        self.assertIn('region_error', poly.Notices)
        self.assertIn('NA', poly.Notices['region_error'])

    def test_call_api_timeout_and_network_exceptions(self):
        """Verifies _callApi catches Timeout and ConnectionError gracefully."""
        from TeslaOauth import teslaAccess
        poly = MockPolyglotInterface()
        oauth = teslaAccess(poly, 'energy_device_data')
        oauth.getAccessToken = lambda: 'test_token'

        import requests

        class MockTimeoutSession:
            def get(self, url, **kwargs):
                raise requests.exceptions.Timeout('Connection timed out')

        oauth._session = MockTimeoutSession()
        res = oauth._callApi('GET', '/products')
        self.assertIsNone(res)

        class MockConnSession:
            def get(self, url, **kwargs):
                raise requests.exceptions.ConnectionError('Network unreachable')

        oauth._session = MockConnSession()
        res2 = oauth._callApi('GET', '/products')
        self.assertIsNone(res2)

    def test_session_close_method(self):
        """Verifies close() closes the session safely."""
        from TeslaOauth import teslaAccess
        poly = MockPolyglotInterface()
        oauth = teslaAccess(poly, 'energy_device_data')
        closed = []
        oauth._session = types.SimpleNamespace(close=lambda: closed.append(True))
        oauth.close()
        self.assertEqual(len(closed), 1)


class TestPhase4BugFixes(unittest.TestCase):
    """Verifies Phase 4 Wall Connector/EV charging telemetry, safe history getters, and drivers."""

    def test_ev_charge_telemetry_history_query(self):
        """Verifies tesla_get_today_history queries telemetry_history for charge kind."""
        from TeslaPWOauth import teslaPWAccess
        poly = MockPolyglotInterface()
        tpw = teslaPWAccess(poly, 'energy_device_data')
        tpw.installation_tz['site_123'] = 'America/New_York'

        api_calls = []
        def mock_call(method, url, body=''):
            api_calls.append(url)
            return {'response': {'charge_history': []}}

        tpw._callApi = mock_call
        tpw.tesla_get_today_history('site_123', 'charge')
        self.assertTrue(len(api_calls) >= 1)
        self.assertIn('telemetry_history?kind=charge', api_calls[0])

    def test_process_charge_data_calculation(self):
        """Verifies process_charge_data parses events and populates history_data with totals."""
        from TeslaPWOauth import teslaPWAccess
        from datetime import datetime
        poly = MockPolyglotInterface()
        tpw = teslaPWAccess(poly, 'energy_device_data')
        tpw.installation_tz['site_123'] = 'America/New_York'
        tpw.update_date_time('site_123')

        # Mock payload matching today's timestamp
        now_ts = int(datetime.now().timestamp())
        charge_payload = {
            'charge_history': [
                {
                    'charge_start_time': {'seconds': now_ts},
                    'charge_duration': {'seconds': 3600},
                    'energy_added_wh': 12500
                },
                {
                    'charge_start_time': {'seconds': now_ts},
                    'charge_duration': {'seconds': 1800},
                    'energy_added_wh': 7500
                }
            ]
        }
        tpw.process_history_data('site_123', 'charge', charge_payload)
        self.assertIn('site_123', tpw.history_data)
        self.assertIn('charge', tpw.history_data['site_123'])
        self.assertIn('today', tpw.history_data['site_123']['charge'])

        today_charge = tpw.history_data['site_123']['charge']['today']
        self.assertEqual(today_charge['total_events'], 2)
        self.assertEqual(today_charge['total_duration'], 5400)
        self.assertEqual(today_charge['total_energy'], 20000)

        self.assertEqual(tpw.tesla_evcharge_power('site_123', 'today'), 20000)
        self.assertEqual(tpw.tesla_evcharge_time('site_123', 'today'), 5400)

    def test_safe_history_getters_missing_site_or_keys(self):
        """Verifies history getters return 0 instead of raising KeyError when site or day is absent."""
        from TeslaPWOauth import teslaPWAccess
        poly = MockPolyglotInterface()
        tpw = teslaPWAccess(poly, 'energy_device_data')

        self.assertEqual(tpw.tesla_evcharge_power('missing_site', 'today'), 0)
        self.assertEqual(tpw.tesla_evcharge_time('missing_site', 'today'), 0)
        self.assertEqual(tpw.tesla_backup_events('missing_site', 'today'), 0)
        self.assertEqual(tpw.tesla_backup_time('missing_site', 'today'), 0)
        self.assertEqual(tpw.tesla_home_energy_total('missing_site', 'today'), 0)
        self.assertEqual(tpw.tesla_battery_energy_import('missing_site', 'today'), 0)
        self.assertEqual(tpw.tesla_grid_energy_export('missing_site', 'today'), 0)

    def test_history_node_ev_charging_drivers(self):
        """Verifies teslaPWHistoryNode updates GV26-GV29 drivers with EV charge values."""
        from TeslaPWHistoryNode import teslaPWHistoryNode
        poly = MockPolyglotInterface()
        tpw = MockTeslaService()

        tpw.days_evcharge_power = 22.0
        tpw.days_evcharge_time = 120.0
        tpw.yesterday_evcharge_power = 18.0
        tpw.yesterday_evcharge_time = 90.0

        hist_node = teslaPWHistoryNode(poly, 'controller', 'pwhistory', 'Powerwall History', 'site_123', tpw)
        hist_node.updateISYdrivers()

        self.assertEqual(hist_node._driver_values['GV26']['value'], 22.0)
        self.assertEqual(hist_node._driver_values['GV27']['value'], 120.0)
        self.assertEqual(hist_node._driver_values['GV28']['value'], 18.0)
        self.assertEqual(hist_node._driver_values['GV29']['value'], 90.0)


class TestPhase5Features(unittest.TestCase):
    """Tests for Phase 5 features: conditional generator drivers and PWSETUP ST operating mode."""

    def test_dynamic_profile_generator_conditional(self):
        """Verifies build_profile_definition includes/omits generator drivers based on generator_installed."""
        from profile_def import build_profile_definition

        # Without generator
        p_no_gen = build_profile_definition(generator_installed=False)
        pwstatus_no = next(nd for nd in p_no_gen['nodedefs'] if nd['id'] == 'PWSTATUS')
        pwhist_no = next(nd for nd in p_no_gen['nodedefs'] if nd['id'] == 'PWHISTORY')

        pwstatus_no_drivers = [prop['id'] for prop in pwstatus_no['properties']]
        pwhist_no_drivers = [prop['id'] for prop in pwhist_no['properties']]

        self.assertNotIn('GV28', pwstatus_no_drivers)
        self.assertNotIn('GV1', pwhist_no_drivers)
        self.assertNotIn('GV2', pwhist_no_drivers)

        # With generator
        p_gen = build_profile_definition(generator_installed=True)
        pwstatus_gen = next(nd for nd in p_gen['nodedefs'] if nd['id'] == 'PWSTATUS')
        pwhist_gen = next(nd for nd in p_gen['nodedefs'] if nd['id'] == 'PWHISTORY')

        pwstatus_gen_drivers = [prop['id'] for prop in pwstatus_gen['properties']]
        pwhist_gen_drivers = [prop['id'] for prop in pwhist_gen['properties']]

        self.assertIn('GV28', pwstatus_gen_drivers)
        self.assertNotIn('GV1', pwhist_gen_drivers)
        self.assertIn('GV2', pwhist_gen_drivers)

    def test_pwsetup_st_operating_mode_in_profile(self):
        """Verifies PWSETUP uses ST for operating mode and removes GV2."""
        from profile_def import build_profile_definition
        payload = build_profile_definition()
        pwsetup = next(nd for nd in payload['nodedefs'] if nd['id'] == 'PWSETUP')

        props = {p['id']: p['editor'] for p in pwsetup['properties']}
        self.assertIn('ST', props)
        self.assertEqual(props['ST'], 'OPMODE')
        self.assertNotIn('GV2', props)

        # Verify OPMODE cmd inits from ST
        opmode_cmd = next(c for c in pwsetup['cmds']['accepts'] if c['id'] == 'OPMODE')
        self.assertEqual(opmode_cmd['parameters'][0]['init'], 'ST')

    def test_tesla_generator_installed_detection(self):
        """Verifies teslaGeneratorInstalled accurately checks components dict."""
        from TeslaPWOauth import teslaPWAccess
        poly = MockPolyglotInterface()
        oauth = teslaPWAccess(poly, 'energy_device_data')

        oauth.site_info['site_gen'] = {'components': {'generator': True}}
        self.assertTrue(oauth.teslaGeneratorInstalled('site_gen'))

        oauth.site_info['site_no_gen'] = {'components': {'generator': False}}
        self.assertFalse(oauth.teslaGeneratorInstalled('site_no_gen'))

        oauth.site_info['site_empty'] = {'components': {}}
        self.assertFalse(oauth.teslaGeneratorInstalled('site_empty'))

    def test_generator_override_methods(self):
        """Verifies TeslaInfoV2 generator override methods."""
        from TeslaInfoV2 import tesla_info
        tpw = tesla_info(None)
        self.assertFalse(tpw.is_generator_installed())

        tpw.set_generator_override(True)
        self.assertTrue(tpw.is_generator_installed())
        self.assertTrue(tpw.generatorInstalled)

        tpw.set_generator_override(False)
        self.assertFalse(tpw.is_generator_installed())
        self.assertFalse(tpw.generatorInstalled)

        tpw.set_generator_override(None)
        self.assertFalse(tpw.is_generator_installed())

    def test_status_and_history_nodes_omit_generator_drivers(self):
        """Verifies status and history nodes filter out generator drivers when generator not installed."""
        poly = MockPolyglotInterface()
        tpw = MockTeslaService()
        tpw.generatorInstalled = False

        st_node = teslaPWStatusNode(poly, 'controller', 'pwstatus_test', 'Status Node', 'site_123', tpw)
        st_driver_ids = [d['driver'] for d in st_node.drivers]
        self.assertNotIn('GV28', st_driver_ids)

        hist_node = teslaPWHistoryNode(poly, 'controller', 'pwhist_test', 'History Node', 'site_123', tpw)
        hist_driver_ids = [d['driver'] for d in hist_node.drivers]
        self.assertNotIn('GV1', hist_driver_ids)
        self.assertNotIn('GV2', hist_driver_ids)

        # When generator is installed
        poly2 = MockPolyglotInterface()
        tpw_gen = MockTeslaService()
        tpw_gen.generatorInstalled = True

        st_node_gen = teslaPWStatusNode(poly2, 'controller', 'pwstatus_gen', 'Status Node Gen', 'site_123', tpw_gen)
        st_gen_driver_ids = [d['driver'] for d in st_node_gen.drivers]
        self.assertIn('GV28', st_gen_driver_ids)

        hist_node_gen = teslaPWHistoryNode(poly2, 'controller', 'pwhist_gen', 'History Node Gen', 'site_123', tpw_gen)
        hist_gen_driver_ids = [d['driver'] for d in hist_node_gen.drivers]
        self.assertNotIn('GV1', hist_gen_driver_ids)
        self.assertIn('GV2', hist_gen_driver_ids)

    def test_poll_system_data_solar_not_installed_local_polling(self):
        """Verifies pollSystemData safely handles solarInstalled=False without AttributeError."""
        from TeslaInfoV2 import tesla_info
        tpw = tesla_info(None)
        tpw.solarInstalled = False
        tpw.localAccessUp = True
        tpw.TPWcloudAccess = False

        class MockMeter:
            def __init__(self, exp=10.0, imp=5.0):
                self.energy_exported = exp
                self.energy_imported = imp
        class MockMeters:
            def get_meter(self, mtype):
                return MockMeter()
        class MockLocal:
            def get_sitemaster(self):
                return {}
            def get_meters(self):
                return MockMeters()
            def is_authenticated(self):
                return True

        tpw.TPWlocal = MockLocal()
        tpw.meters = MockMeters()
        tpw.DSbatteryMeter = MockMeter()
        tpw.DSloadMeter = MockMeter()
        tpw.DSsiteMeter = MockMeter()

        result = tpw.pollSystemData('site_123', 'all')
        self.assertTrue(result)
        self.assertEqual(tpw.daysTotalSolar, 0.0)

    def test_get_tpw_online_status_detection(self):
        """Verifies getTPW_onLine returns online (1) when local or cloud is working, even if connected_to_tesla is False."""
        from TeslaInfoV2 import tesla_info
        tpw = tesla_info(None)

        # Case 1: Local gateway connected and running, but connected_to_tesla is False
        tpw.localAccessUp = True
        tpw.firstPollCompleted = True
        tpw.status = {'status': 'StatusUp', 'running': True, 'connected_to_tesla': False, 'power_supply_mode': False}
        tpw.cloudAccessUp = False
        tpw.TPWcloudAccess = False
        self.assertEqual(tpw.getTPW_onLine(), 1)
        self.assertEqual(tpw.getTPW_ConnectedTesla(), 0)
        self.assertEqual(tpw.getTPW_powerSupplyMode(), 0)

        # Case 2: Cloud only up
        tpw.localAccessUp = False
        tpw.firstPollCompleted = False
        tpw.TPWcloudAccess = True
        tpw.cloudAccessUp = True
        self.assertEqual(tpw.getTPW_onLine(), 1)

        # Case 3: Cloud only down
        tpw.cloudAccessUp = False
        self.assertEqual(tpw.getTPW_onLine(), 0)

        # Case 4: Neither local nor cloud
        tpw.TPWcloudAccess = False
        self.assertEqual(tpw.getTPW_onLine(), 0)

        # Case 5: Local gateway explicitly down and cloud down
        tpw.localAccessUp = True
        tpw.firstPollCompleted = True
        tpw.status = {'status': 'StatusDown', 'running': False, 'connected_to_tesla': False}
        self.assertEqual(tpw.getTPW_onLine(), 0)




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

    # Extract driver descriptions from dynamic profile definition in code
    driver_descriptions = {}
    profile_payload = build_profile_definition()
    for nd in profile_payload.get('nodedefs', []):
        nid = nd.get('id')
        for prop in nd.get('properties', []):
            driver_descriptions[(nid, prop.get('id'))] = prop.get('name')

    def print_node_table(node, title):
        print(f"\n--- {title} (ID: {node.id}, Address: {node.address}) ---")
        print(f"{'Driver':<7} | {'Description':<28} | {'Value':<10} | {'UOM':<6}")
        print("-" * 60)
        for drv, info in sorted(node._driver_values.items()):
            desc = driver_descriptions.get((node.id, drv), drv)[:28]
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
