from build.rename_guard import resolve_new_stores

WINDOW_START = "2026-05-23"


def test_new_store_with_no_predecessor_is_included():
    history = [
        {"store_name": "PNQ KK Ravet", "first_seen": "2026-07-17", "last_seen": "2026-08-20"},
    ]
    result = resolve_new_stores(history, WINDOW_START)
    assert result == [{"store_name": "PNQ KK Ravet", "launch_date": "2026-07-17", "aliases": ["PNQ KK Ravet"]}]


def test_store_first_seen_before_window_is_excluded():
    history = [
        {"store_name": "HYD KK Manikonda Online", "first_seen": "2025-11-25", "last_seen": "2026-08-21"},
    ]
    result = resolve_new_stores(history, WINDOW_START)
    assert result == []


def test_self_rename_within_window_resolves_to_earliest_date_under_canonical_name():
    history = [
        {"store_name": "BLR KK SB Sarjapura - Krispy Kreme", "first_seen": "2026-07-05", "last_seen": "2026-07-05"},
        {"store_name": "BLR KK SB Sarjapura", "first_seen": "2026-07-06", "last_seen": "2026-08-20"},
    ]
    result = resolve_new_stores(history, WINDOW_START)
    assert result == [{
        "store_name": "BLR KK SB Sarjapura",
        "launch_date": "2026-07-05",
        "aliases": ["BLR KK SB Sarjapura - Krispy Kreme", "BLR KK SB Sarjapura"],
    }]


def test_old_store_renamed_recently_is_excluded_entirely():
    history = [
        {"store_name": "IXC KK Dhillon Plaza", "first_seen": "2026-04-28", "last_seen": "2026-05-27"},
        {"store_name": "IXC KK Dhillon Plaza - Kripsy Kreme - NCR", "first_seen": "2026-05-28", "last_seen": "2026-08-20"},
    ]
    result = resolve_new_stores(history, WINDOW_START)
    assert result == []


def test_weak_single_token_overlap_is_not_treated_as_rename():
    history = [
        {"store_name": "BLR KK Forum", "first_seen": "2025-01-28", "last_seen": "2026-06-28"},
        {"store_name": "BLR KK Forum KML", "first_seen": "2026-07-01", "last_seen": "2026-08-20"},
    ]
    result = resolve_new_stores(history, WINDOW_START)
    assert result == [{"store_name": "BLR KK Forum KML", "launch_date": "2026-07-01", "aliases": ["BLR KK Forum KML"]}]


def test_predecessor_gap_too_large_is_not_treated_as_rename():
    history = [
        {"store_name": "PNQ KK Kothrud Old", "first_seen": "2026-01-01", "last_seen": "2026-06-01"},
        {"store_name": "PNQ KK Kothrud", "first_seen": "2026-07-07", "last_seen": "2026-08-20"},
    ]
    result = resolve_new_stores(history, WINDOW_START)
    assert result == [{"store_name": "PNQ KK Kothrud", "launch_date": "2026-07-07", "aliases": ["PNQ KK Kothrud"]}]


def test_manual_exclude_filters_out_a_known_rename_the_heuristic_missed():
    # "IXC KK Kharar" is a single-word place name, so its rename to
    # "IXC KK Kharar - Kripsy Kreme - NCR" falls below the automatic
    # guard's 2-token overlap threshold. Confirmed against real
    # ClickHouse data that this is actually an old store (true launch
    # 2026-04-30), so it's manually excluded rather than loosening the
    # threshold and risking false merges elsewhere (e.g. "Forum").
    history = [
        {"store_name": "IXC KK Kharar", "first_seen": "2026-04-30", "last_seen": "2026-05-27"},
        {"store_name": "IXC KK Kharar - Kripsy Kreme - NCR", "first_seen": "2026-05-28", "last_seen": "2026-08-21"},
    ]
    result = resolve_new_stores(history, WINDOW_START, manual_excludes={"IXC KK Kharar - Kripsy Kreme - NCR"})
    assert result == []
