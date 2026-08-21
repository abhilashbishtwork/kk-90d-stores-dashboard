from datetime import date
from build.queries import (
    BRAND_ID,
    build_online_history_query,
    build_any_channel_history_query,
    build_revenue_query,
    build_offline_revenue_query,
    build_ops_metrics_query,
)

STORES = ["PNQ KK Ravet", "BLR KK SB Sarjapura - Krispy Kreme", "BLR KK SB Sarjapura"]
START = date(2026, 5, 23)
END = date(2026, 8, 21)


def test_history_query_scopes_to_brand_and_online_channels_only():
    sql = build_online_history_query()
    assert f"brand_id = {BRAND_ID}" in sql
    assert "channel IN ('swiggy', 'zomato', 'ownly')" in sql
    assert "GROUP BY store_name" in sql
    assert "min(toDate(created_at_ist))" in sql
    assert "max(toDate(created_at_ist))" in sql


def test_any_channel_history_query_scopes_to_brand_only_no_channel_filter():
    sql = build_any_channel_history_query()
    assert f"brand_id = {BRAND_ID}" in sql
    assert "channel" not in sql
    assert "GROUP BY store_name" in sql
    assert "min(toDate(created_at_ist))" in sql
    assert "max(toDate(created_at_ist))" in sql


def test_revenue_query_includes_brand_and_all_given_store_aliases():
    sql = build_revenue_query(STORES, START, END)
    assert f"brand_id = {BRAND_ID}" in sql
    assert "'PNQ KK Ravet'" in sql
    assert "'BLR KK SB Sarjapura - Krispy Kreme'" in sql
    assert "'BLR KK SB Sarjapura'" in sql


def test_revenue_query_filters_online_channels_only():
    sql = build_revenue_query(STORES, START, END)
    assert "channel IN ('swiggy', 'zomato', 'ownly')" in sql


def test_revenue_query_excludes_cancelled_via_state_transitions():
    sql = build_revenue_query(STORES, START, END)
    assert "orders_state_transitions" in sql
    assert "'Cancelled', 'customer_cancelled'" in sql


def test_revenue_query_uses_ist_date_bounds():
    sql = build_revenue_query(STORES, START, END)
    assert "toDate('2026-05-23', 'Asia/Kolkata')" in sql
    assert "toDate('2026-08-21', 'Asia/Kolkata')" in sql


def test_offline_revenue_query_scopes_to_pos_channel():
    sql = build_offline_revenue_query(STORES, START, END)
    assert f"brand_id = {BRAND_ID}" in sql
    assert "channel = 'pos'" in sql
    assert "'PNQ KK Ravet'" in sql


def test_offline_revenue_query_does_not_filter_cancellations():
    # Dine-in has no comparable order-state pipeline in this data —
    # same as the Pune/NCR precedent's dine-in revenue query.
    sql = build_offline_revenue_query(STORES, START, END)
    assert "orders_state_transitions" not in sql


def test_offline_revenue_query_uses_ist_date_bounds_and_selects_order_count():
    sql = build_offline_revenue_query(STORES, START, END)
    assert "toDate('2026-05-23', 'Asia/Kolkata')" in sql
    assert "toDate('2026-08-21', 'Asia/Kolkata')" in sql
    assert "order_count" in sql


def test_ops_metrics_query_scoped_to_swiggy_zomato_and_kpt_p80():
    sql = build_ops_metrics_query(STORES, START, END)
    assert "channel IN ('swiggy', 'zomato')" in sql
    assert "quantileIf(0.8)" in sql
