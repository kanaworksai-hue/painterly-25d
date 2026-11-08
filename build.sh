#!/bin/sh
# Build the installable extension zip into dist/ (needs Blender 5.0+ on PATH or BLENDER env var)
set -e
cd "$(dirname "$0")"
BLENDER="${BLENDER:-blender}"
mkdir -p dist
"$BLENDER" --factory-startup --command extension validate painterly_25d
"$BLENDER" --factory-startup --command extension build --source-dir painterly_25d --output-dir dist
