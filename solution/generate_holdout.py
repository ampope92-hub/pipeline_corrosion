"""Generates the hidden holdout stretch the verifier re-runs the agent's program against.

Same export format and the same columns, but a DIFFERENT seed AND a different true intensity:
this is other pipe, on another part of the network, where the coating and soil effects do not
sit the way they do on the shipped stretch. The shipped instance is SEED 0.

Everything graded otherwise comes from the stretch that ships in the agent's image, so a program
could fit once and write the resulting numbers into the Fortran source as a DATA statement. The
verifier swaps /app/data for this stretch and runs the same binary again. seg_ids run P00000..
in both, so a program emitting stored counts returns the right ids carrying counts fitted to
different pipe, and the deviance collapses.

The different regime is what closes the subtler version of that cheat. A program that stores the
FITTED COEFFICIENTS rather than the counts recomputes plausible numbers on whatever it is handed,
so it survives a holdout drawn from the same generator: measured on the previous same-regime
holdout it scored 0.4244, above the 0.20 bar, while an honest refit scored 0.4232. Under this
regime the stored fit scores -0.7566 and the honest refit 0.4182, so only a program that actually
reads history.dat at run time clears the bar.

Writes tests/holdout/{history.dat,survey.dat,survey_truth.dat}.

Usage: python solution/generate_holdout.py <seed>
"""
import hashlib
import pathlib
import sys

from generate_data import make_segments, write_dat

SHIPPED_SEED = 0

# Other pipe: a lower baseline intensity, age and pressure biting less, cathodic protection
# entering with the opposite sign, and the coating and soil rankings reversed. Nothing about the
# export format changes, so a program that refits handles it without noticing.
HOLDOUT_REGIME = {
    "eta0": -2.40,
    "k_age": 0.030,
    "k_cp": -0.0050,
    "k_press": -0.006,
    "coat_k": {"fbe": 0.45, "tape": -0.50, "cte": 0.0},
    "soil_k": {"sand": 0.50, "clay": -0.35, "loam": 0.15, "peat": -0.60},
}
seed = int(sys.argv[1])
if seed == SHIPPED_SEED:
    sys.exit(f"seed {seed} is the shipped export — the holdout must differ")

out = pathlib.Path(__file__).resolve().parent.parent / "tests" / "holdout"
out.mkdir(parents=True, exist_ok=True)
tr, te = make_segments(seed, **HOLDOUT_REGIME)
write_dat(out / "history.dat", tr, len(tr["defects"]), True)
write_dat(out / "survey.dat", te, len(te["defects"]), False)
with open(out / "survey_truth.dat", "w") as fh:
    fh.write("seg_id defects\n")
    fh.writelines(f"P{i:05d} {int(v)}\n" for i, v in enumerate(te["defects"]))

print(f"holdout seed {seed} -> {out}")
for f in ("history.dat", "survey.dat", "survey_truth.dat"):
    b = (out / f).read_bytes()
    print(f"  {f:18s} {len(b):>8d} bytes  sha256 {hashlib.sha256(b).hexdigest()}")
