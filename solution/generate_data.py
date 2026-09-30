"""Pipeline in-line-inspection generator.

The crux is exposure: segment lengths span three orders of magnitude (0.05-40 km), so defect
COUNTS have to be modelled against a log(length) offset. Fitting the observed rate
(defects/length) directly lets a 1-of-2 segment carry the same weight as a 500-of-1000 one.

A per-segment frailty term stands for unmeasured condition (old coating damage, third-party
interference, local drainage). It is what keeps the ceiling short of perfect and makes the
counts genuinely overdispersed.
"""
import numpy as np

COAT = ["fbe", "tape", "cte"]          # coating system
COAT_K = {"fbe": -0.55, "tape": 0.35, "cte": 0.0}
SOIL = ["sand", "clay", "loam", "peat"]
SOIL_K = {"sand": -0.40, "clay": 0.25, "loam": -0.10, "peat": 0.55}


# The shipped stretch's true intensity. The holdout stretch is generated under a DIFFERENT set
# (see generate_holdout.py): a holdout sharing the shipped coefficients is cleared by a program
# that never opens history.dat and carries the shipped fit in its source as a DATA statement.
ETA0, K_AGE, K_CP, K_PRESS = -3.05, 0.052, 0.0035, 0.011
FRAILTY_SD = 0.75


def make_segments(seed=0, n_train=4000, n_test=3000, *, eta0=ETA0, k_age=K_AGE, k_cp=K_CP,
                  k_press=K_PRESS, coat_k=None, soil_k=None, frailty_sd=FRAILTY_SD):
    coat_k = COAT_K if coat_k is None else coat_k
    soil_k = SOIL_K if soil_k is None else soil_k
    rng = np.random.default_rng(seed)

    def block(n):
        # Exposure spans ~3 orders of magnitude: this is what makes the offset matter.
        length_km = np.exp(rng.uniform(np.log(0.05), np.log(40.0), n)).round(3)
        age_yr = rng.uniform(3, 45, n).round(1)
        cp_mv = rng.normal(-880, 90, n).clip(-1200, -550).round(0)   # cathodic protection
        coat = rng.choice(COAT, n)
        soil = rng.choice(SOIL, n)
        op_press_bar = rng.normal(62, 12, n).clip(20, 100).round(1)

        # true defect intensity per km
        eta = (eta0
               + k_age * age_yr
               + k_cp * (cp_mv + 880)
               + np.array([coat_k[c] for c in coat])
               + np.array([soil_k[s] for s in soil])
               + k_press * (op_press_bar - 62))
        # Unmeasured per-segment condition — old coating damage, third-party interference,
        # local drainage. Nothing in the export explains it, so no model can reach it; it is
        # what keeps the achievable ceiling short of perfect and the counts overdispersed.
        frailty = rng.normal(0.0, frailty_sd, n)
        rate = np.exp(eta + frailty)
        defects = rng.poisson(rate * length_km)
        return {"length_km": length_km, "age_yr": age_yr, "cp_mv": cp_mv, "coat": coat,
                "soil": soil, "op_press_bar": op_press_bar, "defects": defects, "rate": rate}

    return block(n_train), block(n_test)


FEATURES = ["length_km", "age_yr", "cp_mv", "coat", "soil", "op_press_bar"]


def write_dat(path, d, n, with_defects):
    """Whitespace-delimited with a header line — Fortran reads this with list-directed input.

    CSV parsing in Fortran is friction, not difficulty, so the export is shipped in the form
    the cell's own tooling would write: fixed columns, one header row, no quoting.
    """
    cols = (["seg_id"] + FEATURES + (["defects"] if with_defects else []))
    with open(path, "w") as fh:
        fh.write(" ".join(cols) + "\n")
        for i in range(n):
            row = [f"P{i:05d}", f"{d['length_km'][i]:.3f}", f"{d['age_yr'][i]:.1f}",
                   f"{d['cp_mv'][i]:.0f}", d["coat"][i], d["soil"][i],
                   f"{d['op_press_bar'][i]:.1f}"]
            if with_defects:
                row.append(str(int(d["defects"][i])))
            fh.write(" ".join(row) + "\n")


if __name__ == "__main__":
    import hashlib
    import pathlib
    import sys

    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    root = pathlib.Path(__file__).resolve().parent.parent
    tr, te = make_segments(seed)
    write_dat(root / "environment/data/history.dat", tr, len(tr["defects"]), True)
    write_dat(root / "environment/data/survey.dat", te, len(te["defects"]), False)
    with open(root / "tests/golden/survey_truth.dat", "w") as fh:
        fh.write("seg_id defects\n")
        fh.writelines(f"P{i:05d} {int(v)}\n" for i, v in enumerate(te["defects"]))
    for f in ("environment/data/history.dat", "environment/data/survey.dat",
              "tests/golden/survey_truth.dat"):
        print(f"{f:36s} sha256 {hashlib.sha256((root / f).read_bytes()).hexdigest()}")
