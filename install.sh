#!/usr/bin/env bash

pip install -r requirements.txt --user

# If profile/ directory exists, archive to profile.static so PG3 uses dynamic JSON profiles instead of static profile.zip
if [ -d "profile" ]; then
    rm -rf profile.static
    mv profile profile.static
fi

# Ensure data/base_profile.json exists
if [ ! -f "data/base_profile.json" ]; then
    python3 scripts/generate_profile_json.py
fi
