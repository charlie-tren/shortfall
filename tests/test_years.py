from datetime import date

from run_build import years_for


def test_new_year_arrives_on_1_april():
    assert years_for("2026-03-31") == (2024, 2023, 2022, 2021)
    assert years_for("2026-04-01") == (2025, 2024, 2023, 2022)


def test_october_2026_scores_fy2025():
    assert years_for(date(2026, 10, 7)) == (2025, 2024, 2023, 2022)


def test_january_still_on_the_year_before_last():
    assert years_for("2027-01-15") == (2025, 2024, 2023, 2022)


def test_depth_is_exactly_four():
    # Tax rate averages over every prior year it is handed; a fifth changes the test.
    for d in ("2026-01-01", "2026-04-01", "2026-12-31", "2030-06-30"):
        ys = years_for(d)
        assert len(ys) == 4 and list(ys) == sorted(ys, reverse=True)
        assert ys[0] - ys[-1] == 3
