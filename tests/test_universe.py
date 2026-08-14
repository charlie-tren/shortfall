import json
import os


def test_universe_shape():
    path = os.path.join(os.path.dirname(__file__), "..", "universe.json")
    names = json.load(open(path))["names"]
    markets = {}
    for n in names:
        markets[n["market"]] = markets.get(n["market"], 0) + 1
    assert len(names) > 690, f"expected ~703 names, got {len(names)}"
    assert markets["United States (NYSE & Nasdaq)"] > 495
    assert markets["Australia (ASX)"] > 195
    assert len(markets) == 2, f"expected exactly 2 markets, got {markets}"
    assert all(n["ticker"] and n["name"] for n in names)
