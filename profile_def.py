"""Dynamic JSON Profile definition in code for PG3/PG3x and IoX.

Follows the dynamic profile architecture used in udi-kidde and udi-nuheatv2:
- Profiles defined entirely in Python code (no runtime XML parsing required).
- UOM 25 ranges define inline value-to-label mappings via 'names': {'<val>': '<label>'}.
- UOM 25 ranges define 'nls' identifiers matching editors.xml for IoX NLS translation table compatibility.
- Top-level 'nls' mapping dictionary is included in the payload for full IoX Admin Console / eisy-ui translation.
- NodeDefs define inline property names, editors, and command definitions.
- Commands under 'sends' (DON, DOF) have no 'name' attribute per UDI PG3x standard.
- All IDs (editors, nodedefs, commands) use uppercase alphanumeric naming without underscores.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List

PROFILE_VERSION = "0.2.3"


def _profile_editors() -> List[Dict[str, Any]]:
    """Return all active editor definitions for the Tesla Powerwall Node Server."""
    return [
        {
            "id": "UPDN",
            "ranges": [
                {
                    "uom": "25",
                    "subset": "0,1",
                    "nls": "UPDN",
                    "names": {
                        "0": "Down",
                        "1": "Up",
                    },
                }
            ],
        },
        {
            "id": "CONNECTION",
            "ranges": [
                {
                    "uom": "25",
                    "subset": "0,1",
                    "nls": "CONNECTION",
                    "names": {
                        "0": "Not Connected",
                        "1": "connected",
                    },
                }
            ],
        },
        {
            "id": "MISS",
            "ranges": [
                {
                    "uom": "55",
                    "min": 0,
                    "max": 255,
                    "prec": 0,
                },
                {
                    "uom": "25",
                    "subset": "98,99",
                    "nls": "ERROR",
                    "names": {
                        "98": "Not defined",
                        "99": "Unknown",
                    },
                },
            ],
        },
        {
            "id": "CONNECTIONTYPE",
            "ranges": [
                {
                    "uom": "25",
                    "subset": "0,1,2,3,99",
                    "nls": "CONNECTIONSTATE",
                    "names": {
                        "0": "No Connection",
                        "1": "Cloud only",
                        "2": "Local only",
                        "3": "Local and Cloud",
                        "99": "Unknown",
                    },
                }
            ],
        },
        {
            "id": "PERCENT",
            "ranges": [
                {
                    "uom": "51",
                    "min": 0,
                    "max": 100,
                    "prec": 0,
                },
                {
                    "uom": "25",
                    "subset": "98,99",
                    "nls": "ERROR",
                    "names": {
                        "98": "Not defined",
                        "99": "Unknown",
                    },
                },
            ],
        },
        {
            "id": "TOGGLE",
            "ranges": [
                {
                    "uom": "25",
                    "subset": "0,1,99",
                    "nls": "ENTOGGLE",
                    "names": {
                        "0": "Disabled",
                        "1": "Enabled",
                        "99": "Unknown",
                    },
                }
            ],
        },
        {
            "id": "SETTOGGLE",
            "ranges": [
                {
                    "uom": "25",
                    "subset": "0,1",
                    "nls": "ENTOGGLE",
                    "names": {
                        "0": "Disabled",
                        "1": "Enabled",
                    },
                }
            ],
        },
        {
            "id": "GRIDMODE",
            "ranges": [
                {
                    "uom": "25",
                    "subset": "0,1,99",
                    "nls": "ENTOGGLE",
                    "names": {
                        "0": "Disabled",
                        "1": "Enabled",
                        "99": "Unknown",
                    },
                }
            ],
        },
        {
            "id": "OPMODE",
            "ranges": [
                {
                    "uom": "25",
                    "subset": "0,1,2,99",
                    "nls": "OPMODE",
                    "names": {
                        "0": "backup",
                        "1": "self consumption",
                        "2": "autonomous",
                        "99": "Unknown",
                    },
                }
            ],
        },
        {
            "id": "SETOPMODE",
            "ranges": [
                {
                    "uom": "25",
                    "subset": "1,2",
                    "nls": "OPMODE",
                    "names": {
                        "1": "self consumption",
                        "2": "autonomous",
                    },
                }
            ],
        },
        {
            "id": "GRIDST",
            "ranges": [
                {
                    "uom": "25",
                    "subset": "0,1,2,3,99",
                    "nls": "ENGRIDSTATUS",
                    "names": {
                        "0": "on grid",
                        "1": "islanded ready",
                        "2": "islanded",
                        "3": "transition to grid",
                        "99": "Unknown code",
                    },
                }
            ],
        },
        {
            "id": "GRIDIMPMODE",
            "ranges": [
                {
                    "uom": "25",
                    "subset": "0,1,99",
                    "nls": "GRIDIMPMODE",
                    "names": {
                        "0": "Allowed",
                        "1": "Not Allowed",
                        "99": "Unknown",
                    },
                }
            ],
        },
        {
            "id": "SETGRIDIMPMODE",
            "ranges": [
                {
                    "uom": "25",
                    "subset": "0,1",
                    "nls": "GRIDIMPMODE",
                    "names": {
                        "0": "Allowed",
                        "1": "Not Allowed",
                    },
                }
            ],
        },
        {
            "id": "GRIDEXPMODE",
            "ranges": [
                {
                    "uom": "25",
                    "subset": "0,1,2,99",
                    "nls": "GRIDEXPMODE",
                    "names": {
                        "0": "PV-only",
                        "1": "Battery-ok",
                        "2": "Never",
                        "99": "Unknown",
                    },
                }
            ],
        },
        {
            "id": "SETGRIDEXPMODE",
            "ranges": [
                {
                    "uom": "25",
                    "subset": "0,1,2",
                    "nls": "GRIDEXPMODE",
                    "names": {
                        "0": "PV-only",
                        "1": "Battery-ok",
                        "2": "Never",
                    },
                }
            ],
        },
        {
            "id": "ONLINE",
            "ranges": [
                {
                    "uom": "25",
                    "subset": "0,1,99",
                    "nls": "ENONLINE",
                    "names": {
                        "0": "offline",
                        "1": "online",
                        "99": "unknown",
                    },
                }
            ],
        },
        {
            "id": "KWH",
            "ranges": [
                {
                    "uom": "33",
                    "min": -100,
                    "max": 100,
                    "prec": 1,
                },
                {
                    "uom": "25",
                    "subset": "98,99",
                    "nls": "NODATA",
                    "names": {
                        "98": "No Data",
                        "99": "No Data",
                    },
                },
            ],
        },
        {
            "id": "KW",
            "ranges": [
                {
                    "uom": "30",
                    "min": -100,
                    "max": 100,
                    "prec": 1,
                },
                {
                    "uom": "25",
                    "subset": "98,99",
                    "nls": "NODATA",
                    "names": {
                        "98": "No Data",
                        "99": "No Data",
                    },
                },
            ],
        },
        {
            "id": "UNIXTIME",
            "ranges": [
                {
                    "uom": "58",
                    "min": 0,
                    "max": 86400,
                    "prec": 0,
                },
                {
                    "uom": "151",
                    "min": 0,
                    "max": 2147483647,
                    "prec": 0,
                },
                {
                    "uom": "25",
                    "subset": "98,99",
                    "nls": "NODATA",
                    "names": {
                        "98": "No Data",
                        "99": "No Data",
                    },
                },
            ],
        },
        {
            "id": "COUNT",
            "ranges": [
                {
                    "uom": "0",
                    "min": 0,
                    "max": 100,
                    "prec": 0,
                },
                {
                    "uom": "25",
                    "subset": "98,99",
                    "nls": "NODATA",
                    "names": {
                        "98": "No Data",
                        "99": "No Data",
                    },
                },
            ],
        },
    ]


def _profile_nodedefs() -> List[Dict[str, Any]]:
    """Return all active nodedef definitions for the Tesla Powerwall Node Server."""
    return [
        {
            "id": "CONTROLLER",
            "nls": "nlscontroller",
            "name": "Tesla PowerWall Info",
            "icon": "Electricity",
            "properties": [
                {"id": "ST", "name": "Controller Up", "editor": "UPDN"},
                {"id": "GV2", "name": "Connected to Tesla Power Wall", "editor": "CONNECTION"},
                {"id": "GV3", "name": "Consecutive missed LongPolls", "editor": "MISS"},
                {"id": "GV4", "name": "Connection Status", "editor": "CONNECTIONTYPE"},
            ],
            "cmds": {
                "accepts": [
                    {"id": "UPDATE", "name": "Update System Data"},
                ],
                "sends": [
                    {"id": "DON"},
                    {"id": "DOF"},
                ],
            },
            "links": {"ctl": [], "rsp": []},
        },
        {
            "id": "PWSTATUS",
            "nls": "nlspwstatus",
            "name": "Power Wall Status",
            "icon": "Electricity",
            "properties": [
                {"id": "ST", "name": "Connected to Tesla", "editor": "ONLINE"},
                {"id": "GV0", "name": "Remaining Battery", "editor": "PERCENT"},
                {"id": "GV1", "name": "Inst Solar Export", "editor": "KW"},
                {"id": "GV2", "name": "Inst Battery Export", "editor": "KW"},
                {"id": "GV3", "name": "Inst Home Load", "editor": "KW"},
                {"id": "GV4", "name": "Inst Grid Import", "editor": "KW"},
                {"id": "GV5", "name": "Operation Mode", "editor": "OPMODE"},
                {"id": "GV6", "name": "Grid Status", "editor": "GRIDST"},
                {"id": "GV7", "name": "Grid Services Active", "editor": "GRIDMODE"},
                {"id": "GV8", "name": "Home Total Use Today", "editor": "KWH"},
                {"id": "GV9", "name": "Solar Export Today", "editor": "KWH"},
                {"id": "GV10", "name": "Battery Export Today", "editor": "KWH"},
                {"id": "GV11", "name": "Battery Import Today", "editor": "KWH"},
                {"id": "GV12", "name": "Grid Export Today", "editor": "KWH"},
                {"id": "GV13", "name": "Grid Import Today", "editor": "KWH"},
                {"id": "GV14", "name": "Grid/House Net Use Today", "editor": "KWH"},
                {"id": "GV28", "name": "Generator Today", "editor": "KWH"},
                {"id": "TIME", "name": "Last Update Time", "editor": "UNIXTIME"},
            ],
            "cmds": {
                "accepts": [
                    {"id": "UPDATE", "name": "Update System Data"},
                ],
                "sends": [],
            },
            "links": {"ctl": [], "rsp": []},
        },
        {
            "id": "PWHISTORY",
            "nls": "nlspwhist",
            "name": "Power Wall History",
            "icon": "Electricity",
            "properties": [
                {"id": "ST", "name": "Connected to Tesla", "editor": "ONLINE"},
                {"id": "GV1", "name": "Generator Today", "editor": "KWH"},
                {"id": "GV2", "name": "Generator Yesterday", "editor": "KWH"},
                {"id": "GV8", "name": "Home Total Use Today", "editor": "KWH"},
                {"id": "GV9", "name": "Solar Export Today", "editor": "KWH"},
                {"id": "GV10", "name": "Battery Export Today", "editor": "KWH"},
                {"id": "GV11", "name": "Battery Import Today", "editor": "KWH"},
                {"id": "GV12", "name": "Grid Export Today", "editor": "KWH"},
                {"id": "GV13", "name": "Grid Import Today", "editor": "KWH"},
                {"id": "GV14", "name": "Grid/House Net Use Today", "editor": "KWH"},
                {"id": "GV15", "name": "Home Total Use Yesterday", "editor": "KWH"},
                {"id": "GV16", "name": "Solar Export Yesterday", "editor": "KWH"},
                {"id": "GV17", "name": "Battery Export Yesterday", "editor": "KWH"},
                {"id": "GV18", "name": "Battery Import Yesterday", "editor": "KWH"},
                {"id": "GV19", "name": "Grid Export Yesterday", "editor": "KWH"},
                {"id": "GV20", "name": "Grid Import Yesterday", "editor": "KWH"},
                {"id": "GV21", "name": "Grid/House Net Use Yesterday", "editor": "KWH"},
                {"id": "GV22", "name": "Today nbr backup events", "editor": "COUNT"},
                {"id": "GV23", "name": "Today backup event time", "editor": "UNIXTIME"},
                {"id": "GV24", "name": "Yesterday nbr backup events", "editor": "COUNT"},
                {"id": "GV25", "name": "Yesterday backup event time", "editor": "UNIXTIME"},
                {"id": "GV26", "name": "Today charge power", "editor": "KWH"},
                {"id": "GV27", "name": "Today charge time", "editor": "UNIXTIME"},
                {"id": "GV28", "name": "Yesterday charge power", "editor": "KWH"},
                {"id": "GV29", "name": "Yesterday charge time", "editor": "UNIXTIME"},
            ],
            "cmds": {
                "accepts": [
                    {"id": "UPDATE", "name": "Update System Data"},
                ],
                "sends": [],
            },
            "links": {"ctl": [], "rsp": []},
        },
        {
            "id": "PWSETUP",
            "nls": "nlspwsetup",
            "name": "Power Wall Control Parameters",
            "icon": "Electricity",
            "properties": [
                {"id": "GV1", "name": "Backup Reserve (%)", "editor": "PERCENT"},
                {"id": "GV2", "name": "Operating Mode", "editor": "OPMODE"},
                {"id": "GV3", "name": "Storm Mode", "editor": "TOGGLE"},
                {"id": "GV5", "name": "Grid Import to battery", "editor": "GRIDIMPMODE"},
                {"id": "GV6", "name": "Grid Export Mode", "editor": "GRIDEXPMODE"},
                {"id": "GV7", "name": "EV offgrid charge reserve (%)", "editor": "PERCENT"},
            ],
            "cmds": {
                "accepts": [
                    {"id": "UPDATE", "name": "Update System Data"},
                    {
                        "id": "BACKUPPCT",
                        "name": "Backup Reserve (%)",
                        "parameters": [
                            {"id": "", "name": "Backup Reserve", "editor": "PERCENT", "init": "GV1"},
                        ],
                    },
                    {
                        "id": "OPMODE",
                        "name": "Operating Mode",
                        "parameters": [
                            {"id": "", "name": "Operating Mode", "editor": "SETOPMODE", "init": "GV2"},
                        ],
                    },
                    {
                        "id": "STORMMODE",
                        "name": "Storm Mode",
                        "parameters": [
                            {"id": "", "name": "Storm Mode", "editor": "SETTOGGLE", "init": "GV3"},
                        ],
                    },
                    {
                        "id": "GRIDMODE",
                        "name": "Grid Operation",
                        "parameters": [
                            {"id": "import", "name": "Grid Import to battery", "editor": "SETGRIDIMPMODE", "init": "GV5"},
                            {"id": "export", "name": "Grid Export Mode", "editor": "SETGRIDEXPMODE", "init": "GV6"},
                        ],
                    },
                    {
                        "id": "EVCHRGMODE",
                        "name": "EV offgrid charge reserve",
                        "parameters": [
                            {"id": "", "name": "EV Reserve", "editor": "PERCENT", "init": "GV7"},
                        ],
                    },
                ],
                "sends": [],
            },
            "links": {"ctl": [], "rsp": []},
        },
    ]


def _build_nls_dictionary() -> Dict[str, str]:
    """Build the comprehensive NLS lookup dictionary for IoX / eisy-ui translation."""
    nls: Dict[str, str] = {}

    # 1. NodeDefs metadata, properties, and commands
    for nd in _profile_nodedefs():
        nid = nd["id"]
        nls_scope = nd.get("nls", nid)
        nls[f"ND-{nid}-NAME"] = nd["name"]
        nls[f"ND-{nid}-ICON"] = nd["icon"]

        for prop in nd.get("properties", []):
            pid = prop["id"]
            pname = prop["name"]
            nls[f"ST-{nls_scope}-{pid}-NAME"] = pname
            if nls_scope != nid:
                nls[f"ST-{nid}-{pid}-NAME"] = pname

        cmds = nd.get("cmds", {})
        for cmd in cmds.get("accepts", []):
            cid = cmd["id"]
            cname = cmd["name"]
            nls[f"CMD-{nls_scope}-{cid}-NAME"] = cname
            if nls_scope != nid:
                nls[f"CMD-{nid}-{cid}-NAME"] = cname
            for p in cmd.get("parameters", []):
                param_id = p.get("id")
                param_name = p.get("name")
                if param_id and param_name:
                    nls[f"CMDP-{param_id}-NAME"] = param_name

    # 2. Discrete value mappings for UOM 25 from editors (including aliases)
    for ed in _profile_editors():
        eid = ed["id"]
        for r in ed.get("ranges", []):
            if str(r.get("uom")) == "25":
                names = r.get("names", {})
                r_nls = r.get("nls")
                for val, label in names.items():
                    nls[f"{eid}-{val}"] = label
                    if r_nls:
                        nls[f"{r_nls}-{val}"] = label

    # Additional standard aliases for legacy / hybrid lookup paths
    aliases = {
        "GRIDSTATUS-0": "on grid",
        "GRIDSTATUS-1": "islanded ready",
        "GRIDSTATUS-2": "islanded",
        "GRIDSTATUS-3": "transition to grid",
        "GRIDSTATUS-99": "Unknown code",
        "GRIDST-0": "on grid",
        "GRIDST-1": "islanded ready",
        "GRIDST-2": "islanded",
        "GRIDST-3": "transition to grid",
        "GRIDST-99": "Unknown code",
        "CONNECTIONSTATE-0": "No Connection",
        "CONNECTIONSTATE-1": "Cloud only",
        "CONNECTIONSTATE-2": "Local only",
        "CONNECTIONSTATE-3": "Local and Cloud",
        "CONNECTIONSTATE-99": "Unknown",
        "CONNECTIONTYPE-0": "No Connection",
        "CONNECTIONTYPE-1": "Cloud only",
        "CONNECTIONTYPE-2": "Local only",
        "CONNECTIONTYPE-3": "Local and Cloud",
        "CONNECTIONTYPE-99": "Unknown",
        "ENTOGGLE-0": "Disabled",
        "ENTOGGLE-1": "Enabled",
        "ENTOGGLE-99": "Unknown",
        "TOGGLE-0": "Disabled",
        "TOGGLE-1": "Enabled",
        "TOGGLE-99": "Unknown",
        "SETTOGGLE-0": "Disabled",
        "SETTOGGLE-1": "Enabled",
        "GRIDMODE-0": "Disabled",
        "GRIDMODE-1": "Enabled",
        "GRIDMODE-99": "Unknown",
        "ENONLINE-0": "offline",
        "ENONLINE-1": "online",
        "ENONLINE-99": "unknown",
        "ONLINE-0": "offline",
        "ONLINE-1": "online",
        "ONLINE-99": "unknown",
        "ERROR-98": "Not defined",
        "ERROR-99": "Unknown",
        "NODATA-98": "No Data",
        "NODATA-99": "No Data",
    }
    nls.update(aliases)

    return nls


def build_profile_definition(version: str = PROFILE_VERSION) -> Dict[str, Any]:
    """Build the complete PG3/PG3x dynamic JSON profile payload."""
    return {
        "version": version,
        "delete": {
            "editors": ["*"],
            "nodedefs": ["*"],
            "linkdefs": ["*"],
        },
        "editors": _profile_editors(),
        "nodedefs": _profile_nodedefs(),
        "linkdefs": [],
        "nls": _build_nls_dictionary(),
    }


def dynamic_profile_payload(version: str = PROFILE_VERSION) -> Dict[str, Any]:
    """Alias for build_profile_definition matching udi-kidde naming."""
    return build_profile_definition(version=version)


if __name__ == "__main__":
    payload = build_profile_definition()
    out_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "base_profile.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"Generated {out_path} with {len(payload['editors'])} editors, {len(payload['nodedefs'])} nodedefs, and {len(payload['nls'])} NLS entries.")
