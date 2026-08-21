"""Turn raw ClickHouse rows into the dashboard's per-store JSON payload.

Unlike Pune/NCR, the roster here is dynamic (see `rename_guard.py`) and
each store may carry more than one historical `store_name` alias (a
pre-rename name that took real orders) — revenue/ops rows must be rolled
up across all of a store's aliases, not just its current canonical name.
"""

from datetime import timedelta

from build.cities import city_for, display_name_for


def _empty_channel_totals():
    return {"swiggy": 0.0, "zomato": 0.0, "ownly": 0.0}


def _empty_window():
    return {"online": 0.0, "total": 0.0, "online_orders": 0}


def _sum_window(daily, start_date_str):
    total = _empty_window()
    for d in daily:
        if d["date"] >= start_date_str:
            total["online"] += sum(d["online"].values())
            total["total"] += d["total"]
            total["online_orders"] += d["online_orders"]
    return total


def build_dashboard_payload(roster, revenue_rows, ops_rows, today_ist):
    today_str = str(today_ist)
    alias_to_canonical = {alias: s["store_name"] for s in roster for alias in s["aliases"]}

    by_store_date = {}
    for r in revenue_rows:
        canonical = alias_to_canonical.get(r["store_name"])
        if canonical is None:
            continue
        key = (canonical, r["order_date"])
        entry = by_store_date.setdefault(key, {"online": _empty_channel_totals(), "online_orders": 0})
        entry["online"][r["channel"]] = entry["online"].get(r["channel"], 0.0) + float(r["revenue"])
        entry["online_orders"] += int(r["order_count"])

    by_store_ops = {}
    for r in ops_rows:
        canonical = alias_to_canonical.get(r["store_name"])
        if canonical is None:
            continue
        kpt_raw = r.get("kpt_p80_minutes", "")
        by_store_ops.setdefault(canonical, []).append({
            "date": r["order_date"],
            "platform": r["channel"].capitalize(),
            "order_count": int(r["total_orders"]),
            "cancelled_orders": int(r["cancelled_orders"]),
            "kpt_p80_minutes": round(float(kpt_raw), 1) if kpt_raw not in ("", None, "nan", "\\N") else None,
        })

    complete_dates = sorted({d for (_, d) in by_store_date if d != today_str})

    wtd_start = str(today_ist - timedelta(days=today_ist.weekday()))
    mtd_start = str(today_ist.replace(day=1))

    stores_out = []
    for store in roster:
        store_name = store["store_name"]
        daily = []
        for d in complete_dates:
            entry = by_store_date.get((store_name, d))
            if entry is None:
                continue
            daily.append({
                "date": d,
                "online": entry["online"],
                "total": sum(entry["online"].values()),
                "online_orders": entry["online_orders"],
            })

        launch_date = store["launch_date"]
        days_since_launch = (today_ist - _parse_date(launch_date)).days

        stores_out.append({
            "store_name": store_name,
            "display_name": display_name_for(store_name),
            "city": city_for(store_name),
            "launch_date": launch_date,
            "days_since_launch": days_since_launch,
            "revenue": {
                "daily": daily,
                "wtd": _sum_window(daily, wtd_start),
                "mtd": _sum_window(daily, mtd_start),
                "lifetime": _sum_window(daily, ""),
            },
            "ops_computed": {
                "daily": sorted(
                    (d for d in by_store_ops.get(store_name, []) if d["date"] != today_str),
                    key=lambda d: d["date"],
                ),
            },
        })

    stores_out.sort(key=lambda s: (s["city"], s["days_since_launch"]))

    return {"stores": stores_out}


def _parse_date(iso_str):
    from datetime import date

    return date.fromisoformat(iso_str)
