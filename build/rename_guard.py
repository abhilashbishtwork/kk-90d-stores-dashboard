"""Resolve the dynamic 90-day-window roster, guarding against store_name
renames being mistaken for new store launches.

Real ClickHouse data for this brand shows two patterns that would corrupt
a naive `first_seen >= window_start` roster:

1. A brand-new store's name settles after a 1-2 day trial tag (e.g.
   "BLR KK SB Sarjapura - Krispy Kreme" for one day, then "BLR KK SB
   Sarjapura" from the next day on). Both names are genuinely new — the
   store should be kept, dated to the earlier name's first_seen.
2. A long-running store gets renamed months into its life (e.g. the IXC
   Chandigarh Tricity cluster renamed on 2026-05-27/28, months after
   their true launch in April). The new name's own first_seen falls
   inside a 90-day window even though the store itself is old — it must
   be excluded.

Both are the same underlying event (a rename): we detect it by requiring
the predecessor name to end almost exactly when the successor name
begins, with a strongly overlapping name. What distinguishes the two
outcomes is purely how old the *resolved* launch date turns out to be.
"""

FILLER_TOKENS = {"kk", "krispy", "kripsy", "kreme", "online", "pos", "offline", "cart", "ncr"}
MAX_GAP_DAYS = 5
MIN_OVERLAP_RATIO = 0.66
MIN_TOKEN_COUNT = 2


def _tokens(store_name):
    cleaned = store_name.lower().replace("-", " ").replace(",", " ").replace(".", " ")
    return [t for t in cleaned.split() if t not in FILLER_TOKENS]


def _days_between(earlier_iso, later_iso):
    from datetime import date

    e = date.fromisoformat(earlier_iso)
    l = date.fromisoformat(later_iso)
    return (l - e).days


def _is_rename(predecessor, candidate):
    if _days_between(predecessor["last_seen"], candidate["first_seen"]) not in range(0, MAX_GAP_DAYS + 1):
        return False

    pred_tokens = _tokens(predecessor["store_name"])
    cand_tokens = _tokens(candidate["store_name"])
    if not pred_tokens or not cand_tokens:
        return False
    if pred_tokens[0] != cand_tokens[0]:
        return False

    pred_rest = set(pred_tokens[1:])
    cand_rest = set(cand_tokens[1:])
    if len(pred_rest) < MIN_TOKEN_COUNT or len(cand_rest) < MIN_TOKEN_COUNT:
        return False

    overlap = len(pred_rest & cand_rest)
    ratio = overlap / min(len(pred_rest), len(cand_rest))
    return ratio >= MIN_OVERLAP_RATIO


def resolve_new_stores(history_rows, window_start, manual_excludes=frozenset()):
    predecessor_of = {}
    for candidate in history_rows:
        best = None
        for predecessor in history_rows:
            if predecessor is candidate:
                continue
            if predecessor["first_seen"] > candidate["first_seen"]:
                continue
            if not _is_rename(predecessor, candidate):
                continue
            gap = _days_between(predecessor["last_seen"], candidate["first_seen"])
            if best is None or gap < best[1]:
                best = (predecessor, gap)
        if best is not None:
            predecessor_of[candidate["store_name"]] = best[0]

    superseded_names = {p["store_name"] for p in predecessor_of.values()}

    results = []
    for row in history_rows:
        if row["store_name"] in superseded_names:
            continue
        if row["store_name"] in manual_excludes:
            continue

        true_launch = row["first_seen"]
        aliases = [row["store_name"]]
        cursor = row
        while cursor["store_name"] in predecessor_of:
            cursor = predecessor_of[cursor["store_name"]]
            true_launch = cursor["first_seen"]
            aliases.insert(0, cursor["store_name"])

        if true_launch >= window_start:
            results.append({
                "store_name": row["store_name"],
                "launch_date": true_launch,
                "aliases": aliases,
            })

    return results
