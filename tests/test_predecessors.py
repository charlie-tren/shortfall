from edgar import CIK_PREDECESSORS, filer_ciks
from fetch_us import build_records, periods_for

XOM_NEW, XOM_OLD = 2115436, 34088
META = {XOM_NEW: {"ticker": "XOM", "name": "Exxon Mobil", "market": "United States (S&P 500)"}}


def frames(duration, instant):
    d, i = periods_for(2025)
    return {d: duration, i: instant}


def test_exxon_reads_its_old_cik():
    assert filer_ciks(XOM_NEW) == (XOM_NEW, XOM_OLD)
    assert filer_ciks(320193) == (320193,)


def test_history_under_the_old_cik_fills_the_new_one():
    # The July 2026 shape: the new CIK has a balance sheet and nothing else.
    f = frames({"Revenues": {XOM_OLD: 332.0}, "NetIncomeLoss": {XOM_OLD: 28.8}},
               {"Assets": {XOM_NEW: 449.0}})
    (r,) = build_records(2025, f, META)
    assert (r.revenue, r.net_income, r.assets) == (332.0, 28.8, 449.0)


def test_the_new_cik_wins_once_it_files():
    f = frames({"Revenues": {XOM_NEW: 340.0, XOM_OLD: 332.0}}, {})
    (r,) = build_records(2025, f, META)
    assert r.revenue == 340.0


def test_no_cik_is_its_own_predecessor():
    for new, olds in CIK_PREDECESSORS.items():
        assert new not in olds and len(set(olds)) == len(olds)


def test_every_year_stays_on_one_tag():
    # Exxon's real shape: the old CIK tags both receivables concepts, the new one
    # only the broader. Taking the new CIK first spliced 35.3bn onto 44.6bn.
    f = frames({}, {"AccountsReceivableNetCurrent": {XOM_OLD: 35.7},
                    "ReceivablesNetCurrent": {XOM_NEW: 44.6, XOM_OLD: 44.6}})
    (r,) = build_records(2025, f, META)
    assert (r.receivables, r.tags["Receivables"]) == (35.7, "AccountsReceivableNetCurrent")
