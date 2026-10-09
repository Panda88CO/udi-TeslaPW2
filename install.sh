#!/usr/bin/env bash

pip install -r requirements.txt --user

# Ensure profile directory exists for base static profile installation
if [ ! -d "profile" ] && [ -d "profile.static" ]; then
    cp -r profile.static profile
fi

# Ensure both lowercase and uppercase NLS files exist for case-sensitive filesystems (FreeBSD / eisy)
if [ -d "profile/nls" ]; then
    cp -f profile/nls/en_us.txt profile/nls/en_US.txt 2>/dev/null || true
fi
if [ -d "profile.static/nls" ]; then
    cp -f profile.static/nls/en_us.txt profile.static/nls/en_US.txt 2>/dev/null || true
fi

# Ensure data/base_profile.json exists
if [ ! -f "data/base_profile.json" ]; then
    python3 scripts/generate_profile_json.py
fi
