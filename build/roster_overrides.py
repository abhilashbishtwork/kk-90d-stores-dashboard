"""Manual escape hatch for renames the automatic guard in `rename_guard.py`
can't safely catch. Add an entry here, with the reasoning and the
confirmed true launch date, whenever a spot-check finds one.

(Kharar/Panchkula, the original reason this file exists, are now caught
automatically by the exact-token-match rule in `_name_signature_match`.)
"""

MANUAL_EXCLUDE_STORE_NAMES = {
    # "PNQ KK FB Baner Pos" (POS-only, first order 2026-07-25) is the
    # dine-in counter of the SAME physical store as the already-tracked
    # online "PNQ KK Baner" (live since 2026-07-02) — not a second, new
    # store. Confirmed via the original kk-pune-dashboard spec (built
    # 2026-08-19), which lists "PNQ KK FB Baner" as one of its 13
    # established stores. The automatic cross-channel dedup in
    # `filter_unknown_places` doesn't catch this pairing because "Baner"
    # (1 remaining token) vs "FB Baner" (2 remaining tokens) falls
    # outside both its exact-match and ratio-with-minimum-token-count
    # rules — a real, accepted blind spot, not a bug to chase further.
    "PNQ KK FB Baner Pos",
}
