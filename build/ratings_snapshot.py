"""One-time Swiggy/Zomato storefront ratings snapshot, as of 2026-08-19.

Pasted by the user from a manual export covering every KK store
nationally; filtered here to just the rows relevant to this dashboard
(a store currently or recently within the 90-day window). Keyed by
`cities.display_name_for()` output rather than the raw ClickHouse
store_name, since the latter can change out from under a rename
(rename_guard resolves a new canonical store_name, but the underlying
place — and its cleaned display name — stays the same).

This is a snapshot, not a live feed — there is no manual CSV to keep
updating (per project scope decision). Re-paste and update
SNAPSHOT_DATE if a fresher export is provided later. A store not in
this dict (e.g. one that launches after the snapshot date) simply shows
as not-yet-rated.
"""

SNAPSHOT_DATE = "2026-08-19"


def _r(rating, count):
    return {"rating": rating, "count": count}


RATINGS_BY_DISPLAY_NAME = {
    "Omaxe Chandni Chowk": {"swiggy": _r(4.2, "<3"), "zomato": _r(None, None)},
    "Niyati Plaza": {"swiggy": _r(4.6, "<3"), "zomato": _r(4.0, 4)},
    "Sangvi": {"swiggy": _r(4.6, "<3"), "zomato": _r(4.0, 3)},
    "Law College": {"swiggy": _r(4.6, "<3"), "zomato": _r(None, None)},
    "Dhanori": {"swiggy": _r(4.6, "<3"), "zomato": _r(None, None)},
    "Hinjewadi": {"swiggy": _r(4.6, "<3"), "zomato": _r(4.0, 5)},
    "Ravet": {"swiggy": _r(4.6, "<3"), "zomato": _r(None, None)},
    "Wagholi": {"swiggy": _r(4.6, 4), "zomato": _r(2.3, 3)},
    "Elan Miracle": {"swiggy": _r(4.2, "<3"), "zomato": _r(2.3, 3)},
    "Kothrud": {"swiggy": _r(4.6, 10), "zomato": _r(4.0, 20)},
    "SB Sarjapura": {"swiggy": _r(4.4, 4), "zomato": _r(4.0, 3)},
    "Pimpri": {"swiggy": _r(4.6, 7), "zomato": _r(4.0, 18)},
    "Viman Nagar": {"swiggy": _r(4.6, 5), "zomato": _r(4.0, 31)},
    "SB Devanahalli": {"swiggy": _r(4.4, 8), "zomato": _r(4.2, 38)},
    # ClickHouse's online store_name for this store is "PNQ KK Baner", but
    # both aggregators list its storefront as "KK FB Baner" — same
    # physical Baner outlet, confirmed by city+area match (no other
    # "Baner" candidate exists in either ratings export).
    "Baner": {"swiggy": _r(4.6, 20), "zomato": _r(4.0, 30)},
    "Amanora": {"swiggy": _r(4.6, 12), "zomato": _r(4.2, 49)},
    "Tribeca": {"swiggy": _r(4.6, 57), "zomato": _r(4.3, 125)},
    "CP 67 Mall": {"swiggy": _r(4.3, 21), "zomato": _r(4.2, 71)},
}

_EMPTY_RATING = {"swiggy": _r(None, None), "zomato": _r(None, None)}


def ratings_for(display_name):
    return RATINGS_BY_DISPLAY_NAME.get(display_name, _EMPTY_RATING)
