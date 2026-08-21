"""Orchestrates the KK 90-day-window ClickHouse pull into data.json.

`run()` takes a `query_runner` callable so it can be unit tested without
a live database; `main()` wires up the real ClickHouse client and is
what the daily cron script actually invokes.
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone

from build.queries import build_online_history_query, build_revenue_query, build_ops_metrics_query
from build.rename_guard import resolve_new_stores
from build.roster_overrides import MANUAL_EXCLUDE_STORE_NAMES
from build.clickhouse_client import run_query
from build.aggregate import build_dashboard_payload
from build.sanity_guard import is_pull_valid

IST = timezone(timedelta(hours=5, minutes=30))
WINDOW_DAYS = 90
DATA_JSON_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data.json")


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
    roster = resolve_new_stores(history_rows, str(window_start), manual_excludes=MANUAL_EXCLUDE_STORE_NAMES)

    if not is_pull_valid(roster, previous_store_count):
        print("ClickHouse pull failed sanity check — keeping existing data.json", file=sys.stderr)
        return False

    all_aliases = [alias for store in roster for alias in store["aliases"]]
    revenue_rows = query_runner(build_revenue_query(all_aliases, window_start, today)) if all_aliases else []
    ops_rows = query_runner(build_ops_metrics_query(all_aliases, window_start, today)) if all_aliases else []

    payload = build_dashboard_payload(roster, revenue_rows, ops_rows, today)
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
