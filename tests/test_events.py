from events import extract_events

RECENT = {
    "form":       ["8-K",   "8-K",  "NT 10-Q", "10-K",  "8-K"],
    "items":      ["4.02",  "5.02", "",        "",      "4.01"],
    "filingDate": ["2025-11-03", "2025-06-01", "2025-02-14", "2025-02-01", "2024-09-09"],
}


def test_extracts_restatement_auditor_change_and_late_filing():
    ev = extract_events(RECENT, as_of="2026-08-14", months=24)
    kinds = {e["kind"] for e in ev}
    assert kinds == {"restatement", "auditor_change", "late_filing"}


def test_respects_lookback_window():
    ev = extract_events(RECENT, as_of="2026-08-14", months=6)
    assert ev == []


def test_ignores_unrelated_8k_items():
    recent = {"form": ["8-K"], "items": ["5.02,9.01"], "filingDate": ["2026-01-01"]}
    assert extract_events(recent, as_of="2026-08-14", months=24) == []


def test_missing_items_field_is_not_an_error():
    # `items` is only populated for 8-Ks and can be absent entirely.
    recent = {"form": ["NT 10-K"], "filingDate": ["2026-01-01"]}
    ev = extract_events(recent, as_of="2026-08-14", months=24)
    assert [e["kind"] for e in ev] == ["late_filing"]


def test_multiple_item_codes_on_one_8k_all_count():
    recent = {"form": ["8-K"], "items": ["4.01,4.02,9.01"], "filingDate": ["2026-01-01"]}
    kinds = {e["kind"] for e in extract_events(recent, as_of="2026-08-14", months=24)}
    assert kinds == {"restatement", "auditor_change"}


def test_malformed_date_is_skipped_not_fatal():
    recent = {"form": ["8-K"], "items": ["4.02"], "filingDate": ["not-a-date"]}
    assert extract_events(recent, as_of="2026-08-14", months=24) == []
