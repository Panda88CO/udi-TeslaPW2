#!/usr/bin/env python3
"""
Generates data/base_profile.json from XML/NLS profile definitions
for Universal Devices PG3x / IoX dynamic JSON profile support.
"""

import os
import sys
import json
import xml.etree.ElementTree as ET

def find_profile_dir(base_dir):
    """Finds either profile or profile.static directory."""
    for cand in ['profile', 'profile.static']:
        p = os.path.join(base_dir, cand)
        if os.path.isdir(p):
            return p
    return os.path.join(base_dir, 'profile')

def parse_editors(path):
    if not os.path.exists(path):
        return []
    tree = ET.parse(path)
    root = tree.getroot()
    editors = []
    for ed in root.findall('editor'):
        ed_id = ed.attrib.get('id')
        ranges = []
        for r in ed.findall('range'):
            r_dict = {}
            for k, v in r.attrib.items():
                if k in ('uom', 'prec'):
                    r_dict[k] = int(v)
                elif k in ('min', 'max'):
                    r_dict[k] = float(v) if '.' in v else int(v)
                else:
                    r_dict[k] = v
            ranges.append(r_dict)
        editors.append({
            'id': ed_id,
            'range': ranges
        })
    return editors

def parse_nodedefs(path):
    if not os.path.exists(path):
        return []
    tree = ET.parse(path)
    root = tree.getroot()
    nodedefs = []
    for nd in root.findall('nodeDef'):
        nd_id = nd.attrib.get('id')
        nls = nd.attrib.get('nls')
        sts = []
        sts_elem = nd.find('sts')
        if sts_elem is not None:
            for st in sts_elem.findall('st'):
                sts.append({
                    'id': st.attrib.get('id'),
                    'editor': st.attrib.get('editor')
                })
        cmds_dict = {'sends': [], 'accepts': []}
        cmds_elem = nd.find('cmds')
        if cmds_elem is not None:
            sends_elem = cmds_elem.find('sends')
            if sends_elem is not None:
                for c in sends_elem.findall('cmd'):
                    cmds_dict['sends'].append({'id': c.attrib.get('id')})
            accepts_elem = cmds_elem.find('accepts')
            if accepts_elem is not None:
                for c in accepts_elem.findall('cmd'):
                    cmd_obj = {'id': c.attrib.get('id')}
                    params = []
                    for p in c.findall('p'):
                        p_dict = {
                            'id': p.attrib.get('id', ''),
                            'editor': p.attrib.get('editor', '')
                        }
                        if 'init' in p.attrib:
                            p_dict['init'] = p.attrib['init']
                        params.append(p_dict)
                    if params:
                        cmd_obj['params'] = params
                    cmds_dict['accepts'].append(cmd_obj)
        nodedefs.append({
            'id': nd_id,
            'nls': nls,
            'sts': sts,
            'cmds': cmds_dict
        })
    return nodedefs

def parse_nls(path):
    if not os.path.exists(path):
        return {}
    nls_dict = {}
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                k, v = line.split('=', 1)
                nls_dict[k.strip()] = v.strip()
    return nls_dict

def generate_profile(base_dir=None):
    if base_dir is None:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    
    profile_dir = find_profile_dir(base_dir)
    editors_path = os.path.join(profile_dir, 'editor', 'editors.xml')
    nodedefs_path = os.path.join(profile_dir, 'nodedef', 'nodedefs.xml')
    nls_path = os.path.join(profile_dir, 'nls', 'en_us.txt')

    editors = parse_editors(editors_path)
    nodedefs = parse_nodedefs(nodedefs_path)
    nls = parse_nls(nls_path)

    profile_data = {
        'editors': editors,
        'nodedefs': nodedefs,
        'nls': nls
    }

    data_dir = os.path.join(base_dir, 'data')
    os.makedirs(data_dir, exist_ok=True)
    out_path = os.path.join(data_dir, 'base_profile.json')

    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(profile_data, f, indent=2)

    print(f"Generated {out_path} with {len(editors)} editors, {len(nodedefs)} nodedefs, and {len(nls)} NLS entries.")
    return profile_data

if __name__ == '__main__':
    generate_profile()

