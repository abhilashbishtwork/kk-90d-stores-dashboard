"""Guard against a bad ClickHouse pull silently wiping the dashboard.

Unlike Pune/NCR's fixed store roster, this roster's size legitimately
changes every day (stores age past 90 days, new ones launch) — so there
is no fixed floor to check against. Instead we compare against
yesterday's resolved roster size and reject an implausible swing.
"""

MAX_SINGLE_DAY_DROP_RATIO = 0.5


def is_pull_valid(roster_rows, previous_store_count):
    if len(roster_rows) == 0:
        return False
    if previous_store_count and len(roster_rows) < previous_store_count * MAX_SINGLE_DAY_DROP_RATIO:
        return False
    return True
