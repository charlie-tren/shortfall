import pytest

from score import (percentile_ranks, composite, coverage_gate,
                   MIN_APPLICABLE_FLAGS, CoverageGateError)


def test_percentile_ranks_higher_value_is_worse():
    ranks = percentile_ranks({"A": 1.0, "B": 2.0, "C": 3.0})
    assert ranks["C"] == 100.0
    assert ranks["A"] == 0.0
    assert 40 < ranks["B"] < 60


def test_percentile_ranks_ignores_none():
    ranks = percentile_ranks({"A": 1.0, "B": None, "C": 3.0})
    assert set(ranks) == {"A", "C"}


def test_percentile_ranks_single_name_sits_mid():
    assert percentile_ranks({"A": 5.0}) == {"A": 50.0}


def test_default_weights_are_not_equal():
    """Accruals is weighted 1.5 and goodwill 1.0, so this is 150/2.5, not the 50
    an equal-weight default would give."""
    assert composite({"accruals": 100.0, "goodwill": 0.0}, weights=None) == 60.0


def test_default_weights_rank_evidence_directness():
    from score import DEFAULT_WEIGHTS
    assert DEFAULT_WEIGHTS["accruals"] > DEFAULT_WEIGHTS["goodwill"]
    assert DEFAULT_WEIGHTS["goodwill"] > DEFAULT_WEIGHTS["stock_comp"]


def test_composite_renormalises_over_applicable_flags_only():
    # goodwill inapplicable: its weight must not silently count as a zero.
    assert composite({"accruals": 80.0}, weights={"accruals": 1.0, "goodwill": 3.0}) == 80.0


def test_composite_respects_weights():
    got = composite({"accruals": 100.0, "goodwill": 0.0},
                    weights={"accruals": 3.0, "goodwill": 1.0})
    assert got == 75.0


def test_composite_none_below_minimum_applicable():
    assert MIN_APPLICABLE_FLAGS == 3
    assert composite({"accruals": 100.0, "goodwill": 50.0}, weights=None,
                     enforce_minimum=True) is None


def test_composite_is_the_worst_two_not_the_mean_of_all():
    # Mean of all three would be 60. Severity takes the worst two: (90+60)/2.
    got = composite({"a": 90.0, "b": 60.0, "c": 30.0}, weights=None, enforce_minimum=True)
    assert got == 75.0


def test_extreme_on_two_beats_mildly_odd_on_six():
    """The whole point of severity. Under a mean-of-all the mild company wins."""
    extreme = composite({"a": 99.0, "b": 97.0, "c": 10.0, "d": 5.0, "e": 5.0, "f": 5.0})
    mild = composite({"a": 65.0, "b": 64.0, "c": 63.0, "d": 62.0, "e": 61.0, "f": 60.0})
    assert extreme > mild
    # And confirm the old aggregator would have got it backwards.
    mean = lambda d: sum(d.values()) / len(d)
    assert mean({"a": 99.0, "b": 97.0, "c": 10.0, "d": 5.0, "e": 5.0, "f": 5.0}) \
        < mean({"a": 65.0, "b": 64.0, "c": 63.0, "d": 62.0, "e": 61.0, "f": 60.0})


def test_a_single_extreme_is_tempered_by_the_second_worst():
    # One test at 100 and nothing else should not top the list on its own.
    lone = composite({"a": 100.0, "b": 2.0, "c": 1.0})
    both = composite({"a": 100.0, "b": 96.0, "c": 1.0})
    assert both > lone
    assert lone == 51.0


def test_composite_none_when_all_weights_zero():
    assert composite({"a": 50.0}, weights={"a": 0.0}) is None


def test_coverage_gate_raises_below_threshold():
    with pytest.raises(CoverageGateError) as e:
        coverage_gate({"accruals": 0.95, "goodwill": 0.42})
    assert "goodwill" in str(e.value)


def test_coverage_gate_passes_at_threshold():
    assert coverage_gate({"accruals": 0.95, "inventory": 0.60}) == ["inventory"]


# --- the JS must agree with the Python -------------------------------------

def test_js_composite_mirrors_python():
    """The page re-scores client side, so a divergence silently changes the
    ranking the moment a reader moves a slider. This caught exactly that: the JS
    was still a plain mean of all six after score.py had moved to severity."""
    import json
    import pathlib
    import re
    import subprocess

    app = pathlib.Path(__file__).resolve().parent.parent / "docs" / "app.js"
    src = app.read_text(encoding="utf-8")
    assert "SEVERITY_TOP_N = 2" in src, "JS lost the severity aggregation"
    # The JS default weights must match DEFAULT_WEIGHTS exactly.
    from score import DEFAULT_WEIGHTS
    block = re.search(r"const DEFAULT_WEIGHTS = \{(.*?)\};", src, re.S).group(1)
    js = dict(re.findall(r"(\w+):\s*([0-9.]+)", block))
    assert {k: float(v) for k, v in js.items()} == DEFAULT_WEIGHTS, \
        f"JS weights {js} != python {DEFAULT_WEIGHTS}"
