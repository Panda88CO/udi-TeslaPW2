#!/usr/bin/env python3
"""
Generates data/base_profile.json from profile_def
for Universal Devices PG3x / IoX dynamic JSON profile support.
"""

import os
import sys
import json

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from profile_def import build_profile_definition

def generate_profile(base_dir=None):
    if base_dir is None:
        base_dir = ROOT_DIR
    
    payload = build_profile_definition()
    data_dir = os.path.join(base_dir, 'data')
    os.makedirs(data_dir, exist_ok=True)
    out_path = os.path.join(data_dir, 'base_profile.json')

    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2)

    print(f"Generated {out_path} with {len(payload['editors'])} editors and {len(payload['nodedefs'])} nodedefs.")
    return payload

if __name__ == '__main__':
    generate_profile()
