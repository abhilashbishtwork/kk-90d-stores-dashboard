from datetime import date
from build.aggregate import build_dashboard_payload

RAVET_ROSTER = [{"store_name": "PNQ KK Ravet", "launch_date": "2026-07-17", "aliases": ["PNQ KK Ravet"]}]
GK1_ROSTER = [{"store_name": "DEL KK GK1 Online", "launch_date": "2026-06-01", "aliases": ["DEL KK GK1 Online"]}]


def test_revenue_rolls_up_across_channels_and_aliases():
    # Sarjapura's canonical name has a 1-day predecessor alias that also
    # took orders — both must roll into the same store entry.
    roster = [{
        "store_name": "BLR KK SB Sarjapura",
        "launch_date": "2026-07-05",
        "aliases": ["BLR KK SB Sarjapura - Krispy Kreme", "BLR KK SB Sarjapura"],
    }]
    revenue_rows = [
        {"order_date": "2026-07-05", "store_name": "BLR KK SB Sarjapura - Krispy Kreme", "channel": "swiggy", "revenue": "300", "order_count": "2"},
        {"order_date": "2026-07-06", "store_name": "BLR KK SB Sarjapura", "channel": "swiggy", "revenue": "1000", "order_count": "10"},
        {"order_date": "2026-07-06", "store_name": "BLR KK SB Sarjapura", "channel": "zomato", "revenue": "500", "order_count": "5"},
    ]
    payload = build_dashboard_payload(roster, revenue_rows, [], [], date(2026, 7, 7))
    store = payload["stores"][0]
    assert len(store["revenue"]["daily"]) == 2
    day0, day1 = store["revenue"]["daily"]
    assert day0["date"] == "2026-07-05"
    assert day0["total"] == 300.0
    assert day1["date"] == "2026-07-06"
    assert day1["online"] == {"swiggy": 1000.0, "zomato": 500.0, "ownly": 0.0}
    assert day1["total"] == 1500.0
    assert day1["online_orders"] == 15
    assert day0["orders_by_channel"] == {"swiggy": 2, "zomato": 0, "ownly": 0}
    assert day1["orders_by_channel"] == {"swiggy": 10, "zomato": 5, "ownly": 0}


def test_offline_revenue_rolls_up_into_dine_in_and_combined_total():
    offline_revenue_rows = [
        {"order_date": "2026-07-05", "store_name": "BLR KK SB Sarjapura", "revenue": "200", "order_count": "3"},
    ]
    roster = [{"store_name": "BLR KK SB Sarjapura", "launch_date": "2026-07-05", "aliases": ["BLR KK SB Sarjapura"]}]
    revenue_rows = [
        {"order_date": "2026-07-05", "store_name": "BLR KK SB Sarjapura", "channel": "swiggy", "revenue": "300", "order_count": "2"},
    ]
    payload = build_dashboard_payload(roster, revenue_rows, offline_revenue_rows, [], date(2026, 7, 6))
    day = payload["stores"][0]["revenue"]["daily"][0]
    assert day["dine_in"] == 200.0
    assert day["dine_in_orders"] == 3
    assert day["total"] == 500.0


def test_offline_only_date_still_produces_a_daily_entry():
    # A day with dine-in activity but zero online orders must still
    # appear in `daily` — complete_dates can't be derived from online
    # rows alone once offline-only stores exist.
    offline_revenue_rows = [
        {"order_date": "2026-08-20", "store_name": "PNQ KK Elpro Mall", "revenue": "150", "order_count": "1"},
    ]
    roster = [{"store_name": "PNQ KK Elpro Mall", "launch_date": "2026-08-20", "aliases": ["PNQ KK Elpro Mall"]}]
    payload = build_dashboard_payload(roster, [], offline_revenue_rows, [], date(2026, 8, 21))
    daily = payload["stores"][0]["revenue"]["daily"]
    assert len(daily) == 1
    assert daily[0]["date"] == "2026-08-20"
    assert daily[0]["dine_in"] == 150.0
    assert daily[0]["online"] == {"swiggy": 0.0, "zomato": 0.0, "ownly": 0.0}
    assert daily[0]["total"] == 150.0


def test_offline_revenue_excluded_for_today_same_as_online():
    offline_revenue_rows = [
        {"order_date": "2026-08-21", "store_name": "PNQ KK Elpro Mall", "revenue": "150", "order_count": "1"},
    ]
    roster = [{"store_name": "PNQ KK Elpro Mall", "launch_date": "2026-08-20", "aliases": ["PNQ KK Elpro Mall"]}]
    payload = build_dashboard_payload(roster, [], offline_revenue_rows, [], date(2026, 8, 21))
    assert payload["stores"][0]["revenue"]["daily"] == []


def test_today_excluded_full_day_rule():
    revenue_rows = [
        {"order_date": "2026-06-01", "store_name": "DEL KK GK1 Online", "channel": "swiggy", "revenue": "999", "order_count": "3"},
    ]
    payload = build_dashboard_payload(GK1_ROSTER, revenue_rows, [], [], date(2026, 6, 1))
    store = payload["stores"][0]
    assert store["revenue"]["daily"] == []


def test_store_with_no_revenue_rows_has_empty_daily_and_zero_totals():
    payload = build_dashboard_payload(RAVET_ROSTER, [], [], [], date(2026, 7, 20))
    store = payload["stores"][0]
    assert store["revenue"]["daily"] == []
    zero = {"online": 0.0, "total": 0.0, "online_orders": 0, "dine_in": 0.0, "dine_in_orders": 0}
    assert store["revenue"]["wtd"] == zero
    assert store["revenue"]["mtd"] == zero
    assert store["revenue"]["lifetime"] == zero
    assert store["ops_computed"]["daily"] == []


def test_mtd_only_sums_current_month():
    revenue_rows = [
        {"order_date": "2026-06-01", "store_name": "DEL KK GK1 Online", "channel": "swiggy", "revenue": "5000", "order_count": "20"},
        {"order_date": "2026-07-01", "store_name": "DEL KK GK1 Online", "channel": "swiggy", "revenue": "300", "order_count": "2"},
    ]
    payload = build_dashboard_payload(GK1_ROSTER, revenue_rows, [], [], date(2026, 7, 2))
    store = payload["stores"][0]
    assert store["revenue"]["mtd"]["total"] == 300.0
    assert store["revenue"]["mtd"]["online_orders"] == 2


def test_lifetime_sums_all_daily_entries_since_launch():
    revenue_rows = [
        {"order_date": "2026-06-01", "store_name": "DEL KK GK1 Online", "channel": "swiggy", "revenue": "5000", "order_count": "20"},
        {"order_date": "2026-07-01", "store_name": "DEL KK GK1 Online", "channel": "swiggy", "revenue": "300", "order_count": "2"},
    ]
    payload = build_dashboard_payload(GK1_ROSTER, revenue_rows, [], [], date(2026, 7, 2))
    store = payload["stores"][0]
    assert store["revenue"]["lifetime"]["total"] == 5300.0
    assert store["revenue"]["lifetime"]["online_orders"] == 22


def test_all_roster_stores_present():
    roster = RAVET_ROSTER + GK1_ROSTER
    payload = build_dashboard_payload(roster, [], [], [], date(2026, 8, 18))
    assert len(payload["stores"]) == 2


def test_city_display_name_and_days_since_launch_computed():
    payload = build_dashboard_payload(RAVET_ROSTER, [], [], [], date(2026, 8, 18))
    store = payload["stores"][0]
    assert store["city"] == "Pune"
    assert store["display_name"] == "Ravet"
    assert store["launch_date"] == "2026-07-17"
    assert store["days_since_launch"] == 32


def test_stores_sorted_by_city_then_most_recently_launched_first():
    roster = [
        {"store_name": "PNQ KK Kothrud", "launch_date": "2026-07-07", "aliases": ["PNQ KK Kothrud"]},
        {"store_name": "PNQ KK Ravet", "launch_date": "2026-07-17", "aliases": ["PNQ KK Ravet"]},
        {"store_name": "BLR KK SB Sarjapura", "launch_date": "2026-07-05", "aliases": ["BLR KK SB Sarjapura"]},
    ]
    payload = build_dashboard_payload(roster, [], [], [], date(2026, 8, 18))
    names = [s["store_name"] for s in payload["stores"]]
    assert names == ["BLR KK SB Sarjapura", "PNQ KK Ravet", "PNQ KK Kothrud"]


def test_ops_computed_cancellation_and_kpt_rolls_up_across_aliases():
    roster = [{
        "store_name": "BLR KK SB Sarjapura",
        "launch_date": "2026-07-05",
        "aliases": ["BLR KK SB Sarjapura - Krispy Kreme", "BLR KK SB Sarjapura"],
    }]
    ops_rows = [
        {"order_date": "2026-07-05", "store_name": "BLR KK SB Sarjapura - Krispy Kreme", "channel": "swiggy",
         "total_orders": "2", "cancelled_orders": "0", "kpt_p80_minutes": "3.4"},
        {"order_date": "2026-07-06", "store_name": "BLR KK SB Sarjapura", "channel": "swiggy",
         "total_orders": "10", "cancelled_orders": "1", "kpt_p80_minutes": "4.1"},
    ]
    payload = build_dashboard_payload(roster, [], [], ops_rows, date(2026, 7, 7))
    ops_daily = payload["stores"][0]["ops_computed"]["daily"]
    assert len(ops_daily) == 2
    assert ops_daily[0]["date"] == "2026-07-05"
    assert ops_daily[0]["order_count"] == 2
    assert ops_daily[1]["cancelled_orders"] == 1
    assert ops_daily[1]["kpt_p80_minutes"] == 4.1


def test_ratings_attached_for_a_known_display_name():
    roster = [{"store_name": "PNQ KK Tribeca", "launch_date": "2026-06-27", "aliases": ["PNQ KK Tribeca"]}]
    payload = build_dashboard_payload(roster, [], [], [], date(2026, 8, 18))
    ratings = payload["stores"][0]["ratings"]
    assert ratings["swiggy"]["rating"] == 4.6
    assert ratings["zomato"]["rating"] == 4.3
    assert ratings["google"]["rating"] is None
    assert ratings["as_of"] == "2026-08-19"


def test_ratings_missing_for_an_unmatched_store_are_null():
    roster = [{"store_name": "DEL KK Brand New Store", "launch_date": "2026-08-18", "aliases": ["DEL KK Brand New Store"]}]
    payload = build_dashboard_payload(roster, [], [], [], date(2026, 8, 18))
    ratings = payload["stores"][0]["ratings"]
    assert ratings["swiggy"]["rating"] is None
    assert ratings["zomato"]["rating"] is None
    assert ratings["google"]["rating"] is None


def test_revenue_before_launch_date_is_excluded_from_daily():
    # Real case: a store that relocated to a new location can have an
    # aliased online store_name whose ClickHouse history predates the
    # relocation by months (the account never stopped ordering) — that
    # pre-relocation revenue must not leak into the new entry's ramp.
    roster = [{"store_name": "BLR KK Mantri Mall", "launch_date": "2026-08-13", "aliases": ["BLR KK Mantri Online"]}]
    revenue_rows = [
        {"order_date": "2026-06-01", "store_name": "BLR KK Mantri Online", "channel": "swiggy", "revenue": "9999", "order_count": "50"},
        {"order_date": "2026-08-14", "store_name": "BLR KK Mantri Online", "channel": "swiggy", "revenue": "500", "order_count": "3"},
    ]
    payload = build_dashboard_payload(roster, revenue_rows, [], [], date(2026, 8, 15))
    daily = payload["stores"][0]["revenue"]["daily"]
    assert len(daily) == 1
    assert daily[0]["date"] == "2026-08-14"
    assert daily[0]["total"] == 500.0


def test_ops_computed_missing_kpt_gives_null():
    ops_rows = [
        {"order_date": "2026-07-17", "store_name": "PNQ KK Ravet", "channel": "zomato",
         "total_orders": "0", "cancelled_orders": "0", "kpt_p80_minutes": "\\N"},
    ]
    payload = build_dashboard_payload(RAVET_ROSTER, [], [], ops_rows, date(2026, 7, 20))
    ops_daily = payload["stores"][0]["ops_computed"]["daily"]
    assert ops_daily[0]["kpt_p80_minutes"] is None
