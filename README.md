# KK New Stores (90d) Dashboard

No-login dashboard tracking every Krispy Kreme store, anywhere in India,
that went live in the trailing 90 days: revenue, orders, cancellation %,
and KPT. Refreshed daily.

Same architecture as `kk-pune-dashboard` and `kk-ncr-dashboard` (static
site on GitHub Pages, Python build script, daily GitHub Actions cron
writing `data.json`) — but the store roster here is **dynamic**, not a
hardcoded list, since which stores qualify changes every day (new ones
launch, old ones age past 90 days).

Live at: https://abhilashbishtwork.github.io/kk-90d-stores-dashboard/

## What's different from Pune/NCR

- **Roster is computed fresh on every build** (`build/rename_guard.py`),
  from `MIN(created_at_ist)` per online `store_name`, nationally, scoped
  to the trailing 90 days.
- **Rename guard**: real ClickHouse data shows store_names get renamed
  (a brand-new store's name settling after a 1-day trial tag, or an old
  store renamed months into its life). A naive `first_seen` query would
  misflag old renamed stores as new. `resolve_new_stores()` walks back
  through rename chains (same city-code prefix, ≥2 overlapping
  non-filler tokens, ≤5-day gap between the old name's last order and
  the new name's first) to find the true launch date, and only keeps a
  store if that true date still falls inside the window. A handful of
  cases fall below the automatic guard's confidence threshold (single-
  word store names, e.g. "Kharar") — those are listed with their
  confirmed true launch date in `build/roster_overrides.py`.
- **City** is derived from the store_name's own prefix convention
  (`build/cities.py`), not a hardcoded per-store mapping — same reason:
  no fixed store list to hang it off.
- **Offline/dine-in (POS) revenue is out of scope** — by explicit
  decision, since mapping each new store's online name to its POS name
  would need constant manual upkeep against a roster that changes daily.
- **No manual ops_metrics.csv** — availability/serviceability/ratings
  are Pune/NCR features that depend on a human updating a CSV per
  store; skipped here for the same roster-churn reason. Cancellation %
  and KPT are still shown — those are computed live from ClickHouse,
  no manual entry needed.
- **Sanity guard** compares today's resolved roster size against
  yesterday's (`data.json`), not a fixed floor — the roster size itself
  is expected to drift day to day as stores enter and exit the window.

## Layout

- `build/` — Python build pipeline (ClickHouse pull → `data.json`).
  Every module has unit tests in `tests/`.
- `assets/dashboard.js`, `assets/alerts.js` — client-side rendering and
  alert logic (`assets/tests/alerts.test.js`, run with `node --test`).
- `.github/workflows/refresh.yml` — daily cron (00:30 IST), also
  runnable manually via `workflow_dispatch`.
- `scripts/refresh_and_deploy.sh` — same refresh, runnable locally.

## Running the build locally

```
cp .env.example .env   # fill in CLICKHOUSE_PASSWORD
python3 -m build.build_data
```

## Tests

```
python3 -m pytest tests/
node --test assets/tests/alerts.test.js
```
