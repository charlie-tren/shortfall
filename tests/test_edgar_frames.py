from edgar import parse_frame


def test_parse_frame_returns_cik_to_value():
    payload = {"tag": "Assets", "data": [
        {"cik": 320193, "entityName": "Apple Inc.", "val": 100},
        {"cik": 1045810, "entityName": "NVIDIA CORP", "val": 200},
    ]}
    assert parse_frame(payload) == {320193: 100.0, 1045810: 200.0}


def test_parse_frame_handles_empty():
    assert parse_frame({"data": []}) == {}


def test_parse_frame_keeps_last_on_duplicate_cik():
    # A filer can appear twice in one frame (amended filings). Last wins.
    payload = {"data": [{"cik": 1, "val": 5}, {"cik": 1, "val": 7}]}
    assert parse_frame(payload) == {1: 7.0}
