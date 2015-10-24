#!/bin/bash
cd "$( dirname "${BASH_SOURCE[0]}" )"

# Keep last N files
KEEP=10
rm -rf $(ls static/gfs/20* -dt|tail -n +$KEEP)
