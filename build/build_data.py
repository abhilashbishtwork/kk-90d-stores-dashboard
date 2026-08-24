"""Orchestrates the KK 90-day-window ClickHouse pull into data.json.

`run()` takes a `query_runner` callable so it can be unit tested without
a live database; `main()` wires up the real ClickHouse client and is
what the daily cron script actually invokes.
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone

from build.queries import (
    build_online_history_query,
    build_any_channel_history_query,
    build_revenue_query,
    build_offline_revenue_query,
    build_ops_metrics_query,
    build_cancellation_detail_query,
    build_discount_detail_query,
)
from build.rename_guard import resolve_new_stores, filter_unknown_places, match_known_places
from build.roster_overrides import MANUAL_EXCLUDE_STORE_NAMES, MANUAL_ALIAS_OVERRIDES, MANUAL_ADDITIONAL_STORES
from build.clickhouse_client import run_query
from build.aggregate import build_dashboard_payload
from build.sanity_guard import is_pull_valid

IST = timezone(timedelta(hours=5, minutes=30))
WINDOW_DAYS = 90
STALE_DAYS = 14
DATA_JSON_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data.json")


def _is_stale(store_name, last_seen_by_name, today, stale_days=STALE_DAYS):
    """A store with no order (any channel) in the last `stale_days` is
    treated as closed/abandoned, not a "new store" worth tracking —
    real case: a kiosk that took 3 orders over 4 days and went silent."""
    last_seen = last_seen_by_name.get(store_name)
    if last_seen is None:
        return False
    from datetime import date

    return (today - date.fromisoformat(last_seen)).days > stale_days


def today_ist():
    return datetime.now(IST).date()


def read_previous_store_count(path):
    if not os.path.exists(path):
        return None
    with open(path) as f:
        try:
            return len(json.load(f).get("stores", []))
        except (json.JSONDecodeError, AttributeError):
            return None


def run(query_runner, today, previous_store_count):
    window_start = today - timedelta(days=WINDOW_DAYS)

    history_rows = query_runner(build_online_history_query())
    online_store_names = {r["store_name"] for r in history_rows}
    roster = resolve_new_stores(history_rows, str(window_start), manual_excludes=MANUAL_EXCLUDE_STORE_NAMES)

    # Stores that have opened (any channel — typically POS/dine-in) but
    # never taken an online order are invisible to the online-only path
    # above. Isolate that offline-only universe, then resolve its own
    # rename chains the same way (the same rename pattern occurs on the
    # POS side, just not simultaneously with the online side).
    any_channel_history_rows = query_runner(build_any_channel_history_query())
    # Names aliased to an already-tracked store (see MANUAL_ALIAS_OVERRIDES)
    # must not also resolve as their own new offline-only entry.
    known_names = online_store_names | set(MANUAL_ALIAS_OVERRIDES)
    offline_only_history = filter_unknown_places(any_channel_history_rows, known_names)
    roster += resolve_new_stores(offline_only_history, str(window_start), manual_excludes=MANUAL_EXCLUDE_STORE_NAMES)

    roster_by_name = {s["store_name"]: s for s in roster}
    for alias_name, target_name in MANUAL_ALIAS_OVERRIDES.items():
        target = roster_by_name.get(target_name)
        if target is not None:
            target["aliases"].append(alias_name)

    # A POS-suffixed (or otherwise differently-named) offline counterpart
    # of an already-tracked online store was correctly excluded above as
    # a duplicate, not a new store — but that dedup must not be a dead
    # end: without wiring it in as an alias here, its offline/POS revenue
    # would never be queried at all (real bug, 2026-08-24: Tribeca,
    # Amanora, CP 67 Mall, Omaxe Chandni Chowk, Elan Miracle and SB
    # Sarjapura all showed zero dine-in revenue for exactly this reason).
    alias_to_canonical = {alias: s["store_name"] for s in roster for alias in s["aliases"]}
    for pos_name, matched_known_name in match_known_places(any_channel_history_rows, known_names).items():
        canonical = alias_to_canonical.get(matched_known_name)
        target = roster_by_name.get(canonical) if canonical else None
        if target is not None and pos_name not in target["aliases"]:
            target["aliases"].append(pos_name)

    # Fully manually-asserted entries (a relocation with no
    # ClickHouse-detectable signal at all) — copy the aliases list so
    # repeated runs never mutate the shared override definition.
    roster += [{**s, "aliases": list(s["aliases"])} for s in MANUAL_ADDITIONAL_STORES]

    last_seen_by_name = {r["store_name"]: r["last_seen"] for r in history_rows}
    last_seen_by_name.update({r["store_name"]: r["last_seen"] for r in any_channel_history_rows})
    roster = [s for s in roster if not _is_stale(s["store_name"], last_seen_by_name, today)]

    if not is_pull_valid(roster, previous_store_count):
        print("ClickHouse pull failed sanity check — keeping existing data.json", file=sys.stderr)
        return False

    all_aliases = [alias for store in roster for alias in store["aliases"]]
    revenue_rows = query_runner(build_revenue_query(all_aliases, window_start, today)) if all_aliases else []
    offline_revenue_rows = query_runner(build_offline_revenue_query(all_aliases, window_start, today)) if all_aliases else []
    ops_rows = query_runner(build_ops_metrics_query(all_aliases, window_start, today)) if all_aliases else []
    cancellation_rows = query_runner(build_cancellation_detail_query(all_aliases, window_start, today)) if all_aliases else []
    discount_rows = query_runner(build_discount_detail_query(all_aliases, window_start, today)) if all_aliases else []

    payload = build_dashboard_payload(roster, revenue_rows, offline_revenue_rows, ops_rows, cancellation_rows, discount_rows, today)
    payload["generated_at_ist"] = datetime.now(IST).isoformat()
    payload["window_days"] = WINDOW_DAYS

    with open(DATA_JSON_PATH, "w") as f:
        json.dump(payload, f, indent=2)

    print(f"Wrote {DATA_JSON_PATH}")
    return True


def main():
    password = os.environ["CLICKHOUSE_PASSWORD"]

    def query_runner(sql):
        return run_query(sql, password)

    previous_store_count = read_previous_store_count(DATA_JSON_PATH)
    ok = run(query_runner, today_ist(), previous_store_count)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
