import json
from datetime import date

from build.build_data import run, read_previous_store_count


def _fake_runner(online_history_rows, revenue_rows, ops_rows, any_channel_history_rows=None,
                  offline_revenue_rows=None, cancellation_rows=None):
    def runner(sql):
        if "cancellation_transitions_pivoted" in sql:
            return cancellation_rows if cancellation_rows is not None else []
        if "transitions_pivoted" in sql:
            return ops_rows
        if "orders_state_transitions" in sql:
            return revenue_rows
        if "channel = 'pos'" in sql:
            return offline_revenue_rows if offline_revenue_rows is not None else []
        if "channel IN" in sql:
            return online_history_rows
        return any_channel_history_rows if any_channel_history_rows is not None else []
    return runner


def test_run_writes_data_json_with_dynamically_resolved_roster(tmp_path, monkeypatch):
    fake_path = tmp_path / "data.json"
    monkeypatch.setattr("build.build_data.DATA_JSON_PATH", str(fake_path))
    monkeypatch.setattr("build.build_data.MANUAL_ADDITIONAL_STORES", [])

    history_rows = [
        {"store_name": "PNQ KK Ravet", "first_seen": "2026-07-17", "last_seen": "2026-08-20"},
        {"store_name": "HYD KK Manikonda Online", "first_seen": "2025-11-25", "last_seen": "2026-08-21"},
    ]
    revenue_rows = [
        {"order_date": "2026-08-17", "store_name": "PNQ KK Ravet", "channel": "swiggy", "revenue": "100", "order_count": "1"},
    ]
    runner = _fake_runner(history_rows, revenue_rows, [])

    result = run(runner, date(2026, 8, 18), previous_store_count=None)

    assert result is True
    written = json.loads(fake_path.read_text())
    assert "generated_at_ist" in written
    # Only the Ravet store falls inside the 90-day window; Manikonda (launched
    # 2025-11-25) does not.
    assert [s["store_name"] for s in written["stores"]] == ["PNQ KK Ravet"]


def test_run_aborts_and_keeps_existing_file_when_roster_is_empty(tmp_path, monkeypatch):
    fake_path = tmp_path / "data.json"
    fake_path.write_text('{"stores": [], "note": "yesterday"}')
    monkeypatch.setattr("build.build_data.DATA_JSON_PATH", str(fake_path))
    monkeypatch.setattr("build.build_data.MANUAL_ADDITIONAL_STORES", [])

    runner = _fake_runner([], [], [])

    result = run(runner, date(2026, 8, 18), previous_store_count=None)

    assert result is False
    assert json.loads(fake_path.read_text())["note"] == "yesterday"


def test_run_aborts_on_implausible_roster_drop(tmp_path, monkeypatch):
    fake_path = tmp_path / "data.json"
    fake_path.write_text('{"stores": [], "note": "yesterday"}')
    monkeypatch.setattr("build.build_data.DATA_JSON_PATH", str(fake_path))

    history_rows = [
        {"store_name": "PNQ KK Ravet", "first_seen": "2026-07-17", "last_seen": "2026-08-20"},
    ]
    runner = _fake_runner(history_rows, [], [])

    # Yesterday's roster had 20 stores; today's pull only resolves 1 — an
    # implausible single-day drop, likely a bad pull rather than reality.
    result = run(runner, date(2026, 8, 18), previous_store_count=20)

    assert result is False
    assert json.loads(fake_path.read_text())["note"] == "yesterday"


def test_run_surfaces_offline_only_store_at_zero_online_revenue(tmp_path, monkeypatch):
    fake_path = tmp_path / "data.json"
    monkeypatch.setattr("build.build_data.DATA_JSON_PATH", str(fake_path))

    online_history_rows = [
        {"store_name": "PNQ KK Ravet", "first_seen": "2026-07-17", "last_seen": "2026-08-20"},
    ]
    any_channel_history_rows = online_history_rows + [
        {"store_name": "PNQ KK Elpro Mall", "first_seen": "2026-08-20", "last_seen": "2026-08-20"},
    ]
    runner = _fake_runner(online_history_rows, [], [], any_channel_history_rows)

    result = run(runner, date(2026, 8, 21), previous_store_count=None)

    assert result is True
    written = json.loads(fake_path.read_text())
    names = [s["store_name"] for s in written["stores"]]
    assert "PNQ KK Elpro Mall" in names
    elpro = next(s for s in written["stores"] if s["store_name"] == "PNQ KK Elpro Mall")
    assert elpro["revenue"]["lifetime"]["total"] == 0.0
    assert elpro["launch_date"] == "2026-08-20"


def test_run_excludes_a_manually_overridden_offline_only_duplicate(tmp_path, monkeypatch):
    # Real case: "PNQ KK FB Baner Pos" is the dine-in counter of the
    # already-tracked online "PNQ KK Baner", per roster_overrides.py.
    fake_path = tmp_path / "data.json"
    monkeypatch.setattr("build.build_data.DATA_JSON_PATH", str(fake_path))

    online_history_rows = [
        {"store_name": "PNQ KK Baner", "first_seen": "2026-07-02", "last_seen": "2026-08-20"},
    ]
    any_channel_history_rows = online_history_rows + [
        {"store_name": "PNQ KK FB Baner Pos", "first_seen": "2026-07-25", "last_seen": "2026-08-20"},
    ]
    runner = _fake_runner(online_history_rows, [], [], any_channel_history_rows)

    result = run(runner, date(2026, 8, 21), previous_store_count=None)

    assert result is True
    names = [s["store_name"] for s in json.loads(fake_path.read_text())["stores"]]
    assert "PNQ KK FB Baner Pos" not in names
    assert "PNQ KK Baner" in names


def test_run_rolls_up_the_alias_overridden_stores_pos_revenue_into_the_target(tmp_path, monkeypatch):
    fake_path = tmp_path / "data.json"
    monkeypatch.setattr("build.build_data.DATA_JSON_PATH", str(fake_path))

    online_history_rows = [
        {"store_name": "PNQ KK Baner", "first_seen": "2026-07-02", "last_seen": "2026-08-20"},
    ]
    any_channel_history_rows = online_history_rows + [
        {"store_name": "PNQ KK FB Baner Pos", "first_seen": "2026-07-25", "last_seen": "2026-08-20"},
    ]
    offline_revenue_rows = [
        {"order_date": "2026-08-17", "store_name": "PNQ KK FB Baner Pos", "revenue": "500", "order_count": "4"},
    ]
    runner = _fake_runner(online_history_rows, [], [], any_channel_history_rows, offline_revenue_rows)

    result = run(runner, date(2026, 8, 18), previous_store_count=None)

    assert result is True
    baner = next(s for s in json.loads(fake_path.read_text())["stores"] if s["store_name"] == "PNQ KK Baner")
    assert baner["revenue"]["lifetime"]["dine_in"] == 500.0


def test_run_excludes_a_store_gone_silent_for_weeks(tmp_path, monkeypatch):
    # Real case: "BLR BIAL SHA POS" took 3 orders over 4 days in early
    # June, then nothing since — an abandoned/test kiosk, not a store
    # worth tracking on a "new stores" dashboard just because its
    # launch date happens to fall in the window.
    fake_path = tmp_path / "data.json"
    monkeypatch.setattr("build.build_data.DATA_JSON_PATH", str(fake_path))

    online_history_rows = [
        {"store_name": "PNQ KK Ravet", "first_seen": "2026-07-17", "last_seen": "2026-08-20"},
    ]
    any_channel_history_rows = online_history_rows + [
        {"store_name": "BLR BIAL SHA POS", "first_seen": "2026-06-04", "last_seen": "2026-06-07"},
    ]
    runner = _fake_runner(online_history_rows, [], [], any_channel_history_rows)

    result = run(runner, date(2026, 8, 21), previous_store_count=None)

    assert result is True
    names = [s["store_name"] for s in json.loads(fake_path.read_text())["stores"]]
    assert "BLR BIAL SHA POS" not in names
    assert "PNQ KK Ravet" in names


def test_run_excludes_an_old_store_renamed_on_the_offline_only_side(tmp_path, monkeypatch):
    # Real bug: "BLR KK- EGL POS" looks brand-new by first_seen alone,
    # but it's a 2026-06-15 rename of the old "BLR Krispy Kreme- EGL
    # POS" (true launch 2025-02-27) — never had an online order, so it
    # must go through the SAME rename-chain resolution as the online
    # side, not a flat first-seen filter.
    fake_path = tmp_path / "data.json"
    monkeypatch.setattr("build.build_data.DATA_JSON_PATH", str(fake_path))

    online_history_rows = [
        {"store_name": "PNQ KK Ravet", "first_seen": "2026-07-17", "last_seen": "2026-08-20"},
    ]
    any_channel_history_rows = online_history_rows + [
        {"store_name": "BLR Krispy Kreme- EGL POS", "first_seen": "2025-02-27", "last_seen": "2026-06-15"},
        {"store_name": "BLR KK- EGL POS", "first_seen": "2026-06-15", "last_seen": "2026-08-20"},
    ]
    runner = _fake_runner(online_history_rows, [], [], any_channel_history_rows)

    result = run(runner, date(2026, 8, 21), previous_store_count=None)

    assert result is True
    names = [s["store_name"] for s in json.loads(fake_path.read_text())["stores"]]
    assert "BLR KK- EGL POS" not in names
    assert "BLR Krispy Kreme- EGL POS" not in names


def test_run_includes_a_manually_added_store_with_its_own_launch_date(tmp_path, monkeypatch):
    # Real case: Mantri Mall relocated to a bigger location on
    # 2026-08-13 but kept ordering through the SAME continuously-active
    # online store_name (no rename, no gap) — there is no ClickHouse
    # signal at all for the relocation date, so it must be asserted
    # manually rather than derived.
    fake_path = tmp_path / "data.json"
    monkeypatch.setattr("build.build_data.DATA_JSON_PATH", str(fake_path))
    monkeypatch.setattr("build.build_data.MANUAL_ADDITIONAL_STORES", [
        {"store_name": "BLR KK Mantri Mall", "launch_date": "2026-08-13", "aliases": ["BLR KK Mantri Online"]},
    ])

    online_history_rows = [
        {"store_name": "PNQ KK Ravet", "first_seen": "2026-07-17", "last_seen": "2026-08-20"},
    ]
    revenue_rows = [
        {"order_date": "2026-06-01", "store_name": "BLR KK Mantri Online", "channel": "swiggy", "revenue": "9999", "order_count": "50"},
        {"order_date": "2026-08-14", "store_name": "BLR KK Mantri Online", "channel": "swiggy", "revenue": "500", "order_count": "3"},
    ]
    runner = _fake_runner(online_history_rows, revenue_rows, [])

    result = run(runner, date(2026, 8, 21), previous_store_count=None)

    assert result is True
    mantri = next(s for s in json.loads(fake_path.read_text())["stores"] if s["store_name"] == "BLR KK Mantri Mall")
    assert mantri["launch_date"] == "2026-08-13"
    assert [d["date"] for d in mantri["revenue"]["daily"]] == ["2026-08-14"]


def test_run_wires_cancellation_detail_rows_into_the_payload(tmp_path, monkeypatch):
    fake_path = tmp_path / "data.json"
    monkeypatch.setattr("build.build_data.DATA_JSON_PATH", str(fake_path))
    monkeypatch.setattr("build.build_data.MANUAL_ADDITIONAL_STORES", [])

    online_history_rows = [
        {"store_name": "PNQ KK Ravet", "first_seen": "2026-07-17", "last_seen": "2026-08-20"},
    ]
    cancellation_rows = [
        {"order_date": "2026-08-17", "store_name": "PNQ KK Ravet", "channel": "swiggy",
         "cancelled_by": "merchant", "cancelled_reason": "store_busy", "cancellation_message": "", "cancelled_orders": "2"},
    ]
    runner = _fake_runner(online_history_rows, [], [], cancellation_rows=cancellation_rows)

    result = run(runner, date(2026, 8, 18), previous_store_count=None)

    assert result is True
    ravet = json.loads(fake_path.read_text())["stores"][0]
    assert ravet["cancellations"]["daily"] == [{
        "date": "2026-08-17", "channel": "swiggy", "cancelled_by": "merchant",
        "reason": "Store busy", "count": 2,
    }]


def test_read_previous_store_count_from_existing_file(tmp_path):
    path = tmp_path / "data.json"
    path.write_text(json.dumps({"stores": [{"store_name": "a"}, {"store_name": "b"}]}))
    assert read_previous_store_count(str(path)) == 2


def test_read_previous_store_count_missing_file_returns_none(tmp_path):
    path = tmp_path / "does_not_exist.json"
    assert read_previous_store_count(str(path)) is None
