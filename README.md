# Pipeline Corrosion Defect Forecast

A gathering-network operator wants to know how many metal-loss indications next season's in-line inspection will find before committing the budget. The agent gets `history.dat`, which lists inspected segments with their adjudicated defect counts and covariates: length, age, cathodic-protection potential, coating, soil and operating pressure. It also gets `survey.dat`, the planned stretch without counts. Working in an offline Fortran project (`/app/predictor`, gfortran only, no numerical libraries), it must fit a model at run time and write `/app/out/predictions.dat` with an expected defect count per surveyed segment. The model is scored on deviance explained relative to a baseline that knows only the network-wide defects-per-kilometre rate and each segment's length.

## What makes it hard

Segment lengths span three orders of magnitude, from under 100 m to about 40 km, and the graded quantity is a count over that length. The correct model is a count GLM (e.g. Poisson) with a `log(length)` offset.

The obvious move is to fit the observed rate (defects / length) and multiply back up. That is wrong: it gives a one-defect, 60 m segment the same weight as a 500-defect, 30 km one, so the noisiest short segments dominate the fit. Worse, it looks healthy. It produces sensible coefficients and a respectable in-sample fit, and fails only when scored as counts against the exposure-aware baseline.

The data dictionary states only how segments are cut (valves, road crossings, survey breaks); it never says an offset is needed. Measured across five generator seeds with the same design matrix and solver:

| Approach | Deviance explained |
|---|---|
| Count model with offset | 0.402 to 0.475 |
| Rate fit | 0.062 to 0.230 |
| Bar | 0.30 |

The instruction notes that a previous model scored 0.11.

The agent must also write iteratively reweighted least squares and a linear solver by hand against gfortran intrinsics. That is real work but not the crux: a flawless solver fitting the rate still fails. A per-segment frailty term makes the counts overdispersed, so the achievable ceiling is well short of perfect.

## How it's graded

The verifier runs in a separate offline container. It recompiles the agent's Fortran project and runs it as an unprivileged user. Nine checks run, six on the shipped stretch and three on a held-back one.

On the shipped stretch:

- The export is unmodified (sha256).
- The header and two-column schema are correct.
- Every surveyed segment appears exactly once.
- Values are finite and non-negative.
- Predictions are not degenerate (they vary across segments).
- Deviance explained against the length-and-rate baseline is at least **0.30**.

The verifier then swaps in a **held-back stretch**, recompiles and reruns. It checks that every segment is covered, that deviance explained is at least **0.20**, and that the output differs from the shipped run.

The held-back stretch is generated under a different true intensity: a lower baseline, the opposite sign on cathodic protection, and reversed coating and soil rankings. A program that stores fitted coefficients rather than refitting on the data it is given scores -0.7566 there, while an honest refit scores 0.4182.

Anti-cheat measures: graded counts are root-only; `/tests` is closed to the build user; only regular output files are staged, which blocks symlinks into the golden data; and pytest runs with `-P`. The reference with only the offset removed (rate fit by least squares) scores 0.0615 and fails both deviance checks. The reference itself explains 0.4070.

## Repository layout

- `instruction.md`: the task prompt given to the agent.
- `task.toml`: metadata, difficulty, solution and verification notes, and resource limits.
- `environment/`: the agent's container (`Dockerfile`), the shipped export with its data dictionary (`data/`) and the Fortran project stub with build script (`predictor/`).
- `solution/`: `solve.sh`, the reference Poisson GLM in Fortran (`main.f90`) and the synthetic data generators (`generate_data.py`, `generate_holdout.py`).
- `tests/`: verifier image and entrypoint (`Dockerfile`, `test.sh`), pytest checks (`test_outputs.py`), the shipped stretch's true counts (`golden/`) and the held-back stretch (`holdout/`).

## Running it

Requires Docker and Harbor (`uv tool install harbor` or `pip install harbor`). From the repo root:

```
harbor run -p . -a oracle
```

This runs the reference solution through the verifier and should score reward 1. To try an agent instead:

```
harbor run -p . -a <agent> -m <model>
```

For example, `-a claude-code`.

---

Task design, data generators, reference solution and verifier by Audrey Pope.
