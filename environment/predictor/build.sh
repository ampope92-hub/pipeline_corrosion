#!/usr/bin/env bash
# Build and run the corrosion predictor. Writes /app/out/predictions.dat.
#   bash /app/predictor/build.sh
set -euo pipefail
cd /app/predictor
mkdir -p /app/out
gfortran -O2 -std=f2008 -o predictor src/main.f90
exec ./predictor
