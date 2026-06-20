from config import load_config
from timing import simulate_durations


def test_typical_duration_is_about_five_to_six_minutes():
    result = simulate_durations(load_config(), 800, simulations=1000, seed=1)
    assert 5.0 <= result["median_minutes"] <= 6.0
    assert result["median_minutes"] <= result["p90_minutes"]
    assert result["start_buffer_seconds_included"] == 5.0


def test_test_mode_duration_is_short():
    result = simulate_durations(load_config("config/test.json"), 2, simulations=100, seed=1)
    assert result["p90_minutes"] < 0.02

