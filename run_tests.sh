#!/bin/bash
# run_tests.sh - Helper script to run tests for SkyHigh Core

echo "=== Installing dependencies ==="
pip install -q pytest pytest-asyncio pytest-cov httpx aiosqlite email-validator

echo ""
echo "=== Running tests ==="
cd /Users/tchakradhar/Documents/untitled/skyhigh-core
python -m pytest tests/ -v --tb=short

echo ""
echo "=== Test Summary ==="
python -m pytest tests/ --co -q | tail -5

