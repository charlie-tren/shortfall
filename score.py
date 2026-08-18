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


# Score on ALL applicable tests, not just the worst two.
#
# Worst-two was the earlier default, on the argument that six near-independent tests
# get diluted by averaging and a short candidate is extreme on one or two rather than
# mildly odd on everything. Measured 18/08/2026, the two orderings share only 15 of
# their top 50 and move the median name 99 places, so the choice is not cosmetic.
#
# All six wins because it uses every observation and is the less opinionated of the
# two, and there is no backtest to justify the opinionated one. The applicability bias
# that worst-two was partly guarding against is handled by the cohort ranking below.
# SEVERITY_TOP_N = None means "use them all".
SEVERITY_TOP_N = None

# Default weights, by HOW DIRECT THE EVIDENCE IS - not equal.
#
# The earlier equal-weight default was justified as "no backtest, so no basis to
# prefer one test". That conflated two things. A backtest would tell you which test
# PREDICTS best, and we do not have one. But how directly a test observes the thing
# it claims to observe is knowable without one, and the tests differ a lot on it.
#
# Accruals is the most studied earnings-quality measure there is (Sloan 1996) and
# measures the gap between profit and cash directly. Stock compensation over revenue
# is a long way from an accounting problem - most of the time it is a pay policy.
# Treating those as equal evidence was the actual unsupported claim.
DEFAULT_WEIGHTS = {
    "accruals": 1.5,          # direct: profit vs cash, and the deepest literature
    "working_capital": 1.25,  # the classic channel for pulling revenue forward
    "goodwill": 1.0,          # real impairment risk, but usually just a deal
    "share_count_roic": 1.0,  # dilution matters, but many benign funding reasons
    "tax_rate": 0.75,         # noisy; mix and one-offs move it for ordinary reasons
    "stock_comp": 0.75,       # weakest inference; often simply competitive pay
}


def composite(flag_scores, weights=None, enforce_minimum=False):
    """Weighted mean over every APPLICABLE test - see SEVERITY_TOP_N above.

    Renormalisation is the point: a test that does not apply has its weight removed
    from the denominator rather than contributing a zero, so a bank is never scored
    as though it passed a test it was never given.
    """
    applicable = {k: v for k, v in flag_scores.items() if v is not None}
    if not applicable:
        return None
    if enforce_minimum and len(applicable) < MIN_APPLICABLE_FLAGS:
        return None
    base = DEFAULT_WEIGHTS if weights is None else weights
    w = {k: base.get(k, 1.0) for k in applicable}
    if not sum(w.values()):
        return None
    scored = sorted(((v * w[k], w[k]) for k, v in applicable.items()),
                    key=lambda t: t[0], reverse=True)
    if SEVERITY_TOP_N:
        scored = scored[:SEVERITY_TOP_N]
    weight_sum = sum(x[1] for x in scored)
    if not weight_sum:
        return None
    return sum(x[0] for x in scored) / weight_sum


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
