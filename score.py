"""Ranking, the weighted composite, and the coverage gate.

THE GATE EXISTS BECAUSE CAPITALISED-COST CREEP DIED AT 8.6%. The same silent
degradation can happen later if filers change their tagging, so the rule that killed
that flag is enforced on every rebuild rather than applied once by hand.

The gate measures APPLICABLE coverage, not raw tag coverage. Inventory is reported by
58.3% of the S&P 500, and most of the rest is banks and software companies that
genuinely hold none - that is applicability, not a data gap.
"""

COVERAGE_FLOOR = 0.60
WARN_BAND = 0.70
MIN_APPLICABLE_FLAGS = 3


class CoverageGateError(Exception):
    """A flag fell below the floor. The build stops rather than thinning silently."""


def percentile_ranks(values):
    """{key: 0-100}, higher meaning more deteriorated. None values are excluded.

    Ranked only against the names to which the flag applies, never against the whole
    universe - otherwise a bank with no inventory would rank as though it passed.
    """
    present = {k: v for k, v in values.items() if v is not None}
    if not present:
        return {}
    ordered = sorted(present.items(), key=lambda kv: kv[1])
    n = len(ordered)
    if n == 1:
        return {ordered[0][0]: 50.0}
    return {k: 100.0 * i / (n - 1) for i, (k, _) in enumerate(ordered)}


def composite(flag_scores, weights=None, enforce_minimum=False):
    """Weighted mean over APPLICABLE flags only.

    Renormalisation is the whole point: if a flag does not apply, its weight is
    removed from the denominator rather than contributing a zero.
    """
    applicable = {k: v for k, v in flag_scores.items() if v is not None}
    if not applicable:
        return None
    if enforce_minimum and len(applicable) < MIN_APPLICABLE_FLAGS:
        return None
    if weights is None:
        return sum(applicable.values()) / len(applicable)
    total = sum(weights.get(k, 1.0) for k in applicable)
    if not total:
        return None
    return sum(v * weights.get(k, 1.0) for k, v in applicable.items()) / total


def coverage_gate(coverage_by_flag):
    """Raise below the floor; return the names in the warning band.

    coverage_by_flag values are fractions of the universe, 0 to 1.
    """
    failed = [k for k, v in coverage_by_flag.items() if v < COVERAGE_FLOOR]
    if failed:
        raise CoverageGateError(
            f"below the {COVERAGE_FLOOR:.0%} coverage floor: "
            + ", ".join(f"{k} at {coverage_by_flag[k]:.1%}" for k in failed)
        )
    return [k for k, v in coverage_by_flag.items() if v < WARN_BAND]
