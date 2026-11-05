"""
RailGuard AI - shared risk rules.

The Flask app, the dataset generator and the model trainer all import this file,
so the "ground truth" logic lives in exactly ONE place.
"""

# --- Thresholds (minutes of spare time after the walk) ---------------------
HIGH_BELOW = 5        # margin < 5            -> High
MEDIUM_BELOW = 15     # 5 <= margin < 15      -> Medium ; margin >= 15 -> Low

CROWD_DELAY = {0: 0, 1: 3}   # 0 = not crowded, 1 = crowded (extra walking minutes)


def base_walk_for_station(max_platform: int) -> int:
    """Bigger station (more platforms) -> longer base walk. Derived from the dataset."""
    if max_platform <= 3:
        return 3
    if max_platform <= 5:
        return 4
    if max_platform <= 7:
        return 5
    if max_platform <= 9:
        return 6
    return 7


def estimate_walk(platform_gap: int, base_walk: int, crowded: int) -> int:
    """Walking minutes to reach the correct platform (0 if already on it)."""
    if platform_gap == 0:
        return 0
    walk = base_walk + int(platform_gap * 1.5) + CROWD_DELAY[int(crowded)]
    return max(2, walk)


def classify_risk(minutes_remaining: int, platform_gap: int, base_walk: int, crowded: int):
    """Return (risk_label, estimated_walk, time_buffer)."""
    walk = estimate_walk(platform_gap, base_walk, crowded)
    buffer_ = minutes_remaining - walk

    if platform_gap == 0:                       # already on the right platform
        return ('Medium' if minutes_remaining <= 2 else 'Low'), 0, buffer_
    if buffer_ < HIGH_BELOW:
        return 'High', walk, buffer_
    if buffer_ < MEDIUM_BELOW:
        return 'Medium', walk, buffer_
    return 'Low', walk, buffer_
