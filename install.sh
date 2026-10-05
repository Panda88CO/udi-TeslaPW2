#!/usr/bin/env bash

pip install -r requirements.txt --user

# Ensure profile directory exists for base static profile installation
if [ ! -d "profile" ] && [ -d "profile.static" ]; then
    cp -r profile.static profile
fi

# Ensure data/base_profile.json exists
if [ ! -f "data/base_profile.json" ]; then
    python3 scripts/generate_profile_json.py
fi
