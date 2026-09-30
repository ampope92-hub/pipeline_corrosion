#!/usr/bin/env bash
set -euo pipefail

# Reference model for the corrosion survey bar.
#
# The counts are modelled against a log(length) offset — a Poisson GLM fitted by iteratively
# reweighted least squares, with the normal equations solved by Gaussian elimination. gfortran
# ships no linear algebra, so the solver is written out; it is thirty lines.
#
# The error the task is built around is fitting the observed RATE (defects/length) directly by
# least squares. That treats a segment with one defect over sixty metres as evidence of the same
# weight as one with five hundred over thirty kilometres, and the graded deviance falls from
# about 0.41 to about 0.06 even though the fitted model looks entirely reasonable on the segments
# it was fitted to.
#
# The model itself is solution/main.f90, next to this script.
install -m 644 "$(dirname "$0")/main.f90" /app/predictor/src/main.f90

bash /app/predictor/build.sh
