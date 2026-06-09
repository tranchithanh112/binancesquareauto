import random
from datetime import datetime, timedelta


def compute_schedule_times(*, base: datetime, count: int, min_minutes: int,
                           max_minutes: int, seed: int | None = None) -> list[datetime]:
    rng = random.Random(seed)
    times = [base]
    current = base
    for _ in range(count - 1):
        delta = rng.randint(min_minutes, max_minutes)
        current = current + timedelta(minutes=delta)
        times.append(current)
    return times
