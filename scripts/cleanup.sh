#!/bin/bash
echo "Pulendo cache Python..."
find /app -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
echo "Cache pulita!"