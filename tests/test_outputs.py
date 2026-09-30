"""Verifier for the corrosion survey model.

test.sh recompiles and runs the agent's Fortran project twice — once on the shipped stretch and
once on a holdout stretch it has never seen — and captures each run's output to a root-only path.
The graded numbers are therefore always the output of a clean build of the agent's own code.

The score is the Poisson deviance explained, against a baseline that knows only the network-wide
defect rate per kilometre and each segment's length. That baseline is what a model gets for free
by respecting exposure at all; beating it requires the covariates to be doing real work. Fitting
the observed rate (defects/length) directly instead of modelling counts against a log(length)
offset lets a segment with one defect over sixty metres carry the same weight as one with five
hundred over thirty kilometres, and the deviance collapses.

Only pytest is installed, so the reading and the arithmetic come from the standard library.
"""

import math
import os
import pathlib

import pytest

# Captured by test.sh; never produced inside pytest, which would run agent code as root.
SURVEY_PRED = pathlib.Path("/opt/run_survey.dat")
HOLDOUT_PRED = pathlib.Path("/opt/run_holdout.dat")
# Root-only copies baked into this image, never in the agent environment.
SURVEY_TRUTH = pathlib.Path("/opt/golden/survey_truth.dat")
HOLDOUT_TRUTH = pathlib.Path("/opt/holdout/survey_truth.dat")
HOLDOUT_SURVEY = pathlib.Path("/opt/holdout/survey.dat")
DATA = pathlib.Path("/app/data")

DEVIANCE_BAR = 0.30
# Slacker: that run exists to show the program refits from what it is handed, not to grade the
# model a second time. A program emitting stored counts scores far below zero here.
HOLDOUT_DEVIANCE_BAR = 0.20

# frozen at task-build time; the shipped export must not be altered
HISTORY_SHA = "d0a2f67b9b14e9bc0d0060ddfac471a567f43e4594d4060be90c2ae0df3f1a26"
SURVEY_SHA = "e795f8747019b9bb6aad7cecfe10f61703d90e14a5c055610ba8592000c319be"


def _open(path, mode="r"):
    """Open without following a final symlink.

    The captured runs are files the agent's own build wrote. test.sh refuses to stage anything
    that is not a regular file, so a link pointing at the answer key never reaches this module;
    opening O_NOFOLLOW here as well means the read cannot be redirected even if it did.
    """
    return os.fdopen(os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW), mode)


def _sha(path):
    import hashlib

    with _open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _rows(path):
    with _open(path) as fh:
        text = fh.read()
    lines = [ln.split() for ln in text.splitlines() if ln.strip()]
    assert lines, f"{path} is empty"
    return lines[0], lines[1:]


def _counts(path, col):
    _, rows = _rows(path)
    return {r[0]: float(r[col]) for r in rows}


def _lengths(path):
    header, rows = _rows(path)
    i = header.index("length_km")
    return {r[0]: float(r[i]) for r in rows}


def _deviance_explained(pred, truth, length):
    """1 - D(model) / D(rate-per-km baseline). Both use the same exposure."""
    ids = sorted(truth)
    total_y = sum(truth[i] for i in ids)
    total_l = sum(length[i] for i in ids)
    rate = total_y / total_l

    def dev(mu_of):
        acc = 0.0
        for i in ids:
            y = truth[i]
            mu = max(mu_of(i), 1e-12)
            term = y * math.log(y / mu) if y > 0 else 0.0
            acc += 2.0 * (term - (y - mu))
        return acc

    base = dev(lambda i: rate * length[i])
    assert base > 0, "the baseline has no deviance to explain"
    return 1.0 - dev(lambda i: pred[i]) / base


@pytest.fixture(scope="session")
def survey_pred():
    assert SURVEY_PRED.exists(), (
        "no /app/out/predictions.dat was produced — `bash /app/predictor/build.sh` must "
        "compile the project and write it"
    )
    return _counts(SURVEY_PRED, 1)


@pytest.fixture(scope="session")
def holdout_pred():
    assert HOLDOUT_PRED.exists(), (
        "the program wrote no predictions when it was run against a second stretch — it must "
        "read and fit from the files in /app/data at run time"
    )
    return _counts(HOLDOUT_PRED, 1)


def test_shipped_export_unmodified():
    """The shipped history.dat and survey.dat are byte-for-byte as issued."""
    assert _sha(DATA / "history.dat") == HISTORY_SHA, "history.dat was altered"
    assert _sha(DATA / "survey.dat") == SURVEY_SHA, "survey.dat was altered"


def test_header_and_schema():
    """The output carries the stated header and two columns per row."""
    header, rows = _rows(SURVEY_PRED)
    assert header == ["seg_id", "expected_defects"], f"header must be 'seg_id expected_defects', got {header}"
    bad = [r for r in rows if len(r) != 2]
    assert not bad, f"every row is two whitespace-separated fields; {len(bad)} are not"


def test_covers_every_segment_exactly_once(survey_pred):
    """Every segment in the survey stretch is quoted exactly once."""
    _, rows = _rows(SURVEY_PRED)
    ids = [r[0] for r in rows]
    assert len(ids) == len(set(ids)), "a seg_id is repeated"
    assert set(ids) == set(_counts(SURVEY_TRUTH, 1)), (
        "the output does not cover exactly the segments in survey.dat"
    )


def test_values_are_finite_and_non_negative(survey_pred):
    """Counts are finite and not negative — a expected count below zero is not a count."""
    for seg, v in survey_pred.items():
        assert math.isfinite(v), f"{seg}: {v} is not finite"
        assert v >= 0.0, f"{seg}: expected_defects is negative ({v})"


def test_predictions_not_degenerate(survey_pred):
    """The predictions vary across segments rather than being one number repeated."""
    vals = list(survey_pred.values())
    spread = (max(vals) - min(vals)) / (sum(vals) / len(vals))
    assert spread > 0.5, (
        f"expected_defects varies by only {spread:.3f} of its mean — segments differ in length "
        "by three orders of magnitude, so a near-constant count is not a model"
    )


def test_deviance_bar(survey_pred):
    """The model explains at least 0.30 of the deviance the rate-per-km baseline leaves."""
    truth = _counts(SURVEY_TRUTH, 1)
    length = _lengths(DATA / "survey.dat")
    score = _deviance_explained(survey_pred, truth, length)
    assert score >= DEVIANCE_BAR, (
        f"deviance explained is {score:.4f}, below the required {DEVIANCE_BAR:.2f} — the "
        "baseline already knows the network-wide rate per kilometre, so this model is adding "
        "little beyond segment length"
    )


def test_holdout_covers_every_segment(holdout_pred):
    """Run on an unseen stretch, the program quotes every segment in it."""
    assert set(holdout_pred) == set(_counts(HOLDOUT_TRUTH, 1)), (
        "the holdout run did not quote exactly the segments in that stretch — the program is "
        "not reading seg_ids from the survey file it was given"
    )


def test_holdout_deviance(holdout_pred):
    """The model still explains the deviance on a stretch the agent never saw."""
    truth = _counts(HOLDOUT_TRUTH, 1)
    length = _lengths(HOLDOUT_SURVEY)
    score = _deviance_explained(holdout_pred, truth, length)
    assert score >= HOLDOUT_DEVIANCE_BAR, (
        f"deviance explained on the holdout stretch is {score:.4f}, below "
        f"{HOLDOUT_DEVIANCE_BAR:.2f}. The same program was graded on the shipped stretch, so "
        "either it is emitting counts fitted to that stretch rather than fitting the files it "
        "was given, or the model does not carry over"
    )


def test_holdout_output_differs_from_shipped_run(survey_pred, holdout_pred):
    """Two different stretches do not produce the same numbers.

    seg_ids run P00000.. in both, so a program that writes counts baked into its source emits an
    identical file both times. Refitting cannot reproduce it.
    """
    shared = sorted(set(survey_pred) & set(holdout_pred))
    assert shared, "the two runs share no seg_ids — cannot compare"
    identical = sum(1 for i in shared if survey_pred[i] == holdout_pred[i])
    assert identical < len(shared) * 0.5, (
        f"{identical} of {len(shared)} segments got identical counts on two different stretches "
        "— the numbers are constants in the source, not a fit to the input"
    )
