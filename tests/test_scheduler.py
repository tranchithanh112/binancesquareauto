from datetime import datetime
from src.poster.scheduler import compute_schedule_times


def test_compute_schedule_times_within_range():
    base = datetime(2026, 6, 8, 8, 0, 0)
    times = compute_schedule_times(base=base, count=5, min_minutes=20,
                                   max_minutes=30, seed=42)
    assert len(times) == 5
    assert times[0] == base
    for i in range(1, 5):
        delta = (times[i] - times[i - 1]).total_seconds() / 60
        assert 20 <= delta <= 30


def test_compute_schedule_times_deterministic_with_seed():
    base = datetime(2026, 6, 8, 8, 0, 0)
    a = compute_schedule_times(base=base, count=3, min_minutes=20, max_minutes=30, seed=1)
    b = compute_schedule_times(base=base, count=3, min_minutes=20, max_minutes=30, seed=1)
    assert a == b
