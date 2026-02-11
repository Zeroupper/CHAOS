#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
docker build -t chaos-sandbox .
echo "Sandbox image 'chaos-sandbox' ready."
