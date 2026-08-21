"""Manual escape hatch for renames the automatic guard in `rename_guard.py`
can't safely catch (single-word store names, below its 2-token overlap
threshold). Add an entry here, with the reasoning and the confirmed true
launch date, whenever a spot-check finds one.
"""

MANUAL_EXCLUDE_STORE_NAMES = {
    # True launch 2026-04-30 (confirmed via ClickHouse); renamed to this
    # on 2026-05-28. "Kharar" is a single token so the automatic guard's
    # overlap-count safety gate doesn't catch it.
    "IXC KK Kharar - Kripsy Kreme - NCR",
    # True launch 2026-04-30 (confirmed via ClickHouse); same reason as above.
    "IXC KK Panchkula - Kripsy Kreme - NCR",
}
