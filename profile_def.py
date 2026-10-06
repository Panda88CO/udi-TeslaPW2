"""Dynamic JSON Profile definition in code for PG3/PG3x and IoX.

Follows the dynamic profile architecture used in udi-kidde and udi-nuheatv2:
- Profiles defined entirely in Python code (no runtime XML parsing required).
- UOM 25 ranges define inline value-to-label mappings via 'names': {'<val>': '<label>'}.
- NodeDefs define inline property names, editors, and command definitions.
- Commands under 'sends' (DON, DOF) have no 'name' attribute per UDI PG3x standard.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List

PROFILE_VERSION = "0.2.2"


def _profile_editors() -> List[Dict[str, Any]]:
    """Return all active editor definitions for the Tesla Powerwall Node Server."""
    return [
        {
            "id": "UPDN",
            "ranges": [
                {
                    "uom": "25",
                    "subset": "0,1",
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
                        "id": "BACKUP_PCT",
                        "name": "Backup Reserve (%)",
                        "parameters": [
                            {"id": "", "name": "Backup Reserve", "editor": "PERCENT", "init": "GV1"},
                        ],
                    },
                    {
                        "id": "OP_MODE",
                        "name": "Operating Mode",
                        "parameters": [
                            {"id": "", "name": "Operating Mode", "editor": "SETOPMODE", "init": "GV2"},
                        ],
                    },
                    {
                        "id": "STORM_MODE",
                        "name": "Storm Mode",
                        "parameters": [
                            {"id": "", "name": "Storm Mode", "editor": "SETTOGGLE", "init": "GV3"},
                        ],
                    },
                    {
                        "id": "GRID_MODE",
                        "name": "Grid Operation",
                        "parameters": [
                            {"id": "import", "name": "Grid Import to battery", "editor": "SETGRIDIMPMODE", "init": "GV5"},
                            {"id": "export", "name": "Grid Export Mode", "editor": "SETGRIDEXPMODE", "init": "GV6"},
                        ],
                    },
                    {
                        "id": "EV_CHRG_MODE",
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
    print(f"Generated {out_path} with {len(payload['editors'])} editors and {len(payload['nodedefs'])} nodedefs.")
