"""Manual escape hatch for renames the automatic guard in `rename_guard.py`
can't safely catch. Add an entry here, with the reasoning and the
confirmed true launch date, whenever a spot-check finds one.

(Kharar/Panchkula, the original reason this file exists, are now caught
automatically by the exact-token-match rule in `_name_signature_match`.)
"""

MANUAL_EXCLUDE_STORE_NAMES = {
    # Confirmed by the user (2026-08-21) not a real store — an
    # onboarding/ops artifact, same class of noise as the tiny
    # same-day artifact rows documented in
    # [[project_krispy_kreme_online_dashboard]].
    "GGN KK ODC GGN",
}

# Cross-channel alias merges: `key` is a store_name that should NOT be
# its own roster entry, but should have its orders rolled into the
# entry canonically named `value`. Distinct from MANUAL_EXCLUDE_STORE_
# NAMES above — that drops a name's data entirely; this preserves it,
# just attributed to the right physical store.
MANUAL_ALIAS_OVERRIDES = {
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
    "PNQ KK FB Baner Pos": "PNQ KK Baner",

    # These three stores relocated to a new/bigger location and kept
    # ordering online through their pre-move aggregator listing (RID) —
    # confirmed directly by the user (2026-08-21), ops-side info
    # ClickHouse's order history can't reveal on its own (no gap or
    # volume step-change at the relocation date, since the account
    # never stopped taking orders). Each of these predecessor names
    # would otherwise resolve as its own old, excluded store (true
    # launch well before the 90-day window) — aliasing them here rolls
    # their ongoing online orders into the relocated store's entry
    # instead, while that entry keeps its own (later, POS-detected)
    # launch_date as the relocation date, not the original RID's.
    "BLR KK Manyata Online": "BLR KK Manyata Tech Park G Block POS",
    "IXC KK Mohali Phase 9 - Kripsy Kreme - NCR": "IXC KK Mohali Walk Pos",
    "JAI KK Vaishali Nagar Online": "JAI KK Mall of Jaipur Pos",
}
