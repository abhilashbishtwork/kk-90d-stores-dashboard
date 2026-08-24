from build.rename_guard import resolve_new_stores, filter_unknown_places, match_known_places

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


def test_filter_unknown_places_keeps_a_genuinely_unrelated_store():
    history = [{"store_name": "PNQ KK Elpro Mall", "first_seen": "2026-08-20", "last_seen": "2026-08-20"}]
    result = filter_unknown_places(history, known_names={"PNQ KK Ravet"})
    assert result == history


def test_filter_unknown_places_drops_an_exact_name_match():
    history = [{"store_name": "PNQ KK Ravet", "first_seen": "2026-07-17", "last_seen": "2026-08-20"}]
    result = filter_unknown_places(history, known_names={"PNQ KK Ravet"})
    assert result == []


def test_filter_unknown_places_drops_a_pos_suffixed_variant_of_a_known_online_name():
    # "DEL KK Omaxe Chandni Chowk Pos" is the same physical store as the
    # already-tracked online "DEL KK Omaxe Chandni Chowk" — must not
    # resurface as a second, zero-revenue phantom entry.
    history = [{"store_name": "DEL KK Omaxe Chandni Chowk Pos", "first_seen": "2026-07-19", "last_seen": "2026-08-20"}]
    result = filter_unknown_places(history, known_names={"DEL KK Omaxe Chandni Chowk"})
    assert result == []


def test_filter_unknown_places_drops_an_exact_single_token_match():
    # A single-word place name (no room for a 2-token overlap check) is
    # still confidently the same place when its remaining token set is
    # *exactly* equal, not just similar.
    history = [{"store_name": "IXC KK Kharar Pos", "first_seen": "2026-07-19", "last_seen": "2026-08-20"}]
    result = filter_unknown_places(history, known_names={"IXC KK Kharar - Kripsy Kreme - NCR"})
    assert result == []


def test_filter_unknown_places_keeps_a_different_single_token_place_in_the_same_city():
    history = [{"store_name": "IXC KK Mohali Walk", "first_seen": "2026-07-19", "last_seen": "2026-08-20"}]
    result = filter_unknown_places(history, known_names={"IXC KK Kharar - Kripsy Kreme - NCR"})
    assert result == history


def test_match_known_places_is_the_complement_of_filter_unknown_places():
    # A POS-suffixed variant of an already-tracked online store is
    # dropped by filter_unknown_places (correctly — it's not a new,
    # offline-only store) but that dedup must not be a dead end: the
    # match itself needs to be returned so the caller can wire the POS
    # name in as an alias of the online store it belongs to, or that
    # store's offline revenue silently goes untracked.
    history = [{"store_name": "DEL KK Omaxe Chandni Chowk Pos", "first_seen": "2026-07-19", "last_seen": "2026-08-20"}]
    result = match_known_places(history, known_names={"DEL KK Omaxe Chandni Chowk"})
    assert result == {"DEL KK Omaxe Chandni Chowk Pos": "DEL KK Omaxe Chandni Chowk"}


def test_match_known_places_returns_exact_match_as_itself():
    history = [{"store_name": "PNQ KK Ravet", "first_seen": "2026-07-17", "last_seen": "2026-08-20"}]
    result = match_known_places(history, known_names={"PNQ KK Ravet"})
    assert result == {"PNQ KK Ravet": "PNQ KK Ravet"}


def test_match_known_places_omits_genuinely_unrelated_stores():
    history = [{"store_name": "PNQ KK Elpro Mall", "first_seen": "2026-08-20", "last_seen": "2026-08-20"}]
    result = match_known_places(history, known_names={"PNQ KK Ravet"})
    assert result == {}
