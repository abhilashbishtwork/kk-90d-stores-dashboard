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


def _name_signature_match(name_a, name_b):
    """True if two store_names plausibly name the same physical place —
    same leading city/area code, plus a strongly overlapping set of
    remaining non-filler tokens. No time component: this is a pure
    name-identity check, reused both for rename-chain detection (with an
    added time-adjacency requirement) and for cross-channel dedup."""
    tokens_a = _tokens(name_a)
    tokens_b = _tokens(name_b)
    if not tokens_a or not tokens_b:
        return False
    if tokens_a[0] != tokens_b[0]:
        return False

    rest_a = set(tokens_a[1:])
    rest_b = set(tokens_b[1:])
    if not rest_a or not rest_b:
        return False

    # An *exact* remaining-token match (e.g. {"kharar"} == {"kharar"}, or
    # {"egl"} == {"egl"}) is strong evidence on its own, even for a
    # single distinctive place-name token — this is what catches
    # single-word renames (Kharar, Panchkula, EGL) that the ratio
    # threshold below deliberately can't, without loosening that
    # threshold and risking false merges between genuinely different
    # generically-named places (e.g. "Forum" vs "Forum KML").
    if rest_a == rest_b:
        return True

    if len(rest_a) < MIN_TOKEN_COUNT or len(rest_b) < MIN_TOKEN_COUNT:
        return False

    overlap = len(rest_a & rest_b)
    ratio = overlap / min(len(rest_a), len(rest_b))
    return ratio >= MIN_OVERLAP_RATIO


def _is_rename(predecessor, candidate):
    if _days_between(predecessor["last_seen"], candidate["first_seen"]) not in range(0, MAX_GAP_DAYS + 1):
        return False
    return _name_signature_match(predecessor["store_name"], candidate["store_name"])


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


def _matching_known_name(store_name, known_names):
    if store_name in known_names:
        return store_name
    for known in known_names:
        if _name_signature_match(store_name, known):
            return known
    return None


def filter_unknown_places(history_rows, known_names):
    """Drop any row that is the same physical place (exactly or by name
    signature) as one of `known_names`.

    Used to isolate the offline-only universe — stores that have opened
    (any channel, typically POS/dine-in) but never taken an online
    order — from the full any-channel history, *before* running that
    subset back through `resolve_new_stores`. A POS-suffixed variant of
    an already-tracked online store_name (e.g. "X Pos" alongside "X")
    must not resurface here as a phantom second entry; a genuine
    offline-only rename (the same June-2026 rename pattern occurs on
    the POS side too) still needs the full rename-chain treatment, not
    a flat first-seen filter, so this only trims duplicates against the
    *known* (online) universe — it does not resolve offline-only
    rename chains itself.
    """
    return [row for row in history_rows if _matching_known_name(row["store_name"], known_names) is None]


def match_known_places(history_rows, known_names):
    """The complement of `filter_unknown_places`: for every row that IS
    the same physical place as one of `known_names`, return
    {row_store_name: matched_known_name}.

    Dropping a POS-suffixed variant as a duplicate (filter_unknown_places)
    must not be a dead end — the caller needs to know *which* known store
    it belongs to, so that name can be wired in as an alias and its
    offline/POS revenue actually gets pulled. Without this, a store with
    both a substantial online history and a differently-suffixed POS
    name would correctly avoid a phantom duplicate roster entry, but its
    POS revenue would then silently never be queried at all.
    """
    result = {}
    for row in history_rows:
        match = _matching_known_name(row["store_name"], known_names)
        if match is not None:
            result[row["store_name"]] = match
    return result
