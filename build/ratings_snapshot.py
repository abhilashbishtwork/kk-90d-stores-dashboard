"""One-time Swiggy/Zomato storefront ratings snapshot, as of 2026-08-24.

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
this dict (e.g. one that launches after the snapshot date, or has no
match in either export yet — Elpro Mall/Nexus Elante Mall/GIP Mall/
Manyata Tech Park G Block as of this snapshot) simply shows as
not-yet-rated.
"""

SNAPSHOT_DATE = "2026-08-24"


def _r(rating, count):
    return {"rating": rating, "count": count}


RATINGS_BY_DISPLAY_NAME = {
    "Omaxe Chandni Chowk": {"swiggy": _r(4.2, "<3"), "zomato": _r(None, None)},
    "Niyati Plaza": {"swiggy": _r(4.3, 3), "zomato": _r(None, None)},
    "Sangvi": {"swiggy": _r(4.3, "<3"), "zomato": _r(4.0, 5)},
    "Law College": {"swiggy": _r(4.3, 3), "zomato": _r(4.0, 8)},
    "Dhanori": {"swiggy": _r(4.3, 4), "zomato": _r(3.3, 3)},
    "Hinjewadi": {"swiggy": _r(4.3, "<3"), "zomato": _r(4.0, 8)},
    "Ravet": {"swiggy": _r(4.3, "<3"), "zomato": _r(4.0, 4)},
    "Wagholi": {"swiggy": _r(4.3, 4), "zomato": _r(2.3, 3)},
    "Elan Miracle": {"swiggy": _r(4.2, "<3"), "zomato": _r(2.3, 3)},
    "Kothrud": {"swiggy": _r(4.3, 10), "zomato": _r(4.0, 24)},
    "SB Sarjapura": {"swiggy": _r(4.4, 4), "zomato": _r(4.1, 3)},
    "Pimpri": {"swiggy": _r(4.3, 7), "zomato": _r(4.0, 18)},
    "Viman Nagar": {"swiggy": _r(4.3, 6), "zomato": _r(4.0, 31)},
    "SB Devanahalli": {"swiggy": _r(4.4, 8), "zomato": _r(4.1, 40)},
    # ClickHouse's online store_name for this store is "PNQ KK Baner", but
    # both aggregators list its storefront as "KK FB Baner" — same
    # physical Baner outlet, confirmed by city+area match (no other
    # "Baner" candidate exists in either ratings export).
    "Baner": {"swiggy": _r(4.1, 21), "zomato": _r(4.0, 30)},
    "Amanora": {"swiggy": _r(4.3, 14), "zomato": _r(4.2, 52)},
    "Tribeca": {"swiggy": _r(4.5, 62), "zomato": _r(4.3, 135)},
    "CP 67 Mall": {"swiggy": _r(4.3, 21), "zomato": _r(4.2, 73)},
    "Mantri Mall": {"swiggy": _r(4.6, "5.2K+"), "zomato": _r(4.2, "2,189")},
    "Mohali Walk": {"swiggy": _r(4.5, 34), "zomato": _r(4.0, 77)},
    "Mall of Jaipur": {"swiggy": _r(4.0, 108), "zomato": _r(4.1, 208)},
    "Karnal Haveli": {"swiggy": _r(3.5, 5), "zomato": _r(3.3, 11)},
    "Dhillon Plaza": {"swiggy": _r(4.2, 36), "zomato": _r(4.2, 98)},
    "Kharar": {"swiggy": _r(4.3, 46), "zomato": _r(4.1, 69)},
    "Panchkula": {"swiggy": _r(4.2, 36), "zomato": _r(4.3, 109)},
    "Sector 24": {"swiggy": _r(4.0, 49), "zomato": _r(4.2, 174)},
}

# No Google storefront ratings data has been provided yet — every store
# shows as not-yet-rated for Google until a snapshot is pasted here,
# same shape as RATINGS_BY_DISPLAY_NAME's swiggy/zomato entries.
GOOGLE_BY_DISPLAY_NAME = {}

_EMPTY_RATING = {"swiggy": _r(None, None), "zomato": _r(None, None)}


def ratings_for(display_name):
    base = RATINGS_BY_DISPLAY_NAME.get(display_name, _EMPTY_RATING)
    return {**base, "google": GOOGLE_BY_DISPLAY_NAME.get(display_name, _r(None, None))}
