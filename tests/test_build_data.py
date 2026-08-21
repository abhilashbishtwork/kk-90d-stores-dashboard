import json
from datetime import date

from build.build_data import run, read_previous_store_count


def _fake_runner(history_rows, revenue_rows, ops_rows):
    def runner(sql):
        if "transitions_pivoted" in sql:
            return ops_rows
        if "orders_state_transitions" in sql:
            return revenue_rows
        return history_rows
    return runner


def test_run_writes_data_json_with_dynamically_resolved_roster(tmp_path, monkeypatch):
    fake_path = tmp_path / "data.json"
    monkeypatch.setattr("build.build_data.DATA_JSON_PATH", str(fake_path))

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


def test_read_previous_store_count_from_existing_file(tmp_path):
    path = tmp_path / "data.json"
    path.write_text(json.dumps({"stores": [{"store_name": "a"}, {"store_name": "b"}]}))
    assert read_previous_store_count(str(path)) == 2


def test_read_previous_store_count_missing_file_returns_none(tmp_path):
    path = tmp_path / "does_not_exist.json"
    assert read_previous_store_count(str(path)) is None
