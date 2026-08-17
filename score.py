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


SEVERITY_TOP_N = 2

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
    """Severity: the weighted mean of a company's WORST TWO applicable tests.

    NOT the mean of all six, which is what this used to be. The correlation matrix
    is why: the tests are near-independent (mean |rho| 0.058), so averaging all of
    them rewards a company that is mildly odd on everything and buries one that is
    extreme on two. The second is the interesting company.

    Measured on the built universe, the mean-of-all version ranked Supermicro 70th,
    AES 323rd, Archer-Daniels-Midland 397th and Crown Castle dead last at 656 - every
    company that had actually disclosed an accounting problem sat mid-table or worse,
    while an airport sat near the top.

    Weights still apply, and are still renormalised over applicable tests only, so a
    reader who cranks one slider changes WHICH tests are most likely to be a company's
    worst two.
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
    # A weight scales how much a test counts towards being one of the worst two.
    scored = sorted(((v * w[k], w[k]) for k, v in applicable.items()),
                    key=lambda t: t[0], reverse=True)[:SEVERITY_TOP_N]
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
