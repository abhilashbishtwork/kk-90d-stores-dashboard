"""One-time Swiggy/Zomato storefront ratings snapshot, as of 2026-09-29.

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
match in either export yet — Elpro Mall/JM Road/Nexus Elante Mall/
Medavakkam/GIP Mall/Pacific Tagore Garden Mall/all 5 new Mumbai stores
as of this snapshot) simply shows as not-yet-rated.
"""

SNAPSHOT_DATE = "2026-09-29"


def _r(rating, count):
    return {"rating": rating, "count": count}


RATINGS_BY_DISPLAY_NAME = {
    "Omaxe Chandni Chowk": {"swiggy": _r(4.2, 5), "zomato": _r(None, 0)},
    "Niyati Plaza": {"swiggy": _r(4.3, 10), "zomato": _r(4.3, 22)},
    "Sangvi": {"swiggy": _r(4.3, 7), "zomato": _r(4.3, 18)},
    "Law College": {"swiggy": _r(4.3, 11), "zomato": _r(4.3, 31)},
    "Dhanori": {"swiggy": _r(4.3, 9), "zomato": _r(4.3, 26)},
    "Hinjewadi": {"swiggy": _r(4.3, 14), "zomato": _r(4.3, 23)},
    "Ravet": {"swiggy": _r(4.3, 12), "zomato": _r(4.3, 17)},
    "Wagholi": {"swiggy": _r(None, 0), "zomato": _r(4.3, 3)},
    "Elan Miracle": {"swiggy": _r(4.1, 3), "zomato": _r(3.0, 3)},
    "Kothrud": {"swiggy": _r(4.3, 17), "zomato": _r(4.3, 45)},
    "SB Sarjapura": {"swiggy": _r(4.3, 7), "zomato": _r(4.1, 5)},
    "Pimpri": {"swiggy": _r(4.3, 14), "zomato": _r(4.3, 38)},
    "Viman Nagar": {"swiggy": _r(4.3, 15), "zomato": _r(4.3, 55)},
    "SB Devanahalli": {"swiggy": _r(4.3, 11), "zomato": _r(4.1, 68)},
    # ClickHouse's online store_name for this store is "PNQ KK Baner", but
    # both aggregators list its storefront as "KK FB Baner" — same
    # physical Baner outlet, confirmed by city+area match (no other
    # "Baner" candidate exists in either ratings export).
    "Baner": {"swiggy": _r(4.3, 36), "zomato": _r(4.3, 65)},
    "Amanora": {"swiggy": _r(4.0, 22), "zomato": _r(4.3, 85)},
    "Tribeca": {"swiggy": _r(4.6, 103), "zomato": _r(4.3, 205)},
    "CP 67 Mall": {"swiggy": _r(4.4, 24), "zomato": _r(4.2, 108)},
    "Mantri Mall": {"swiggy": _r(4.6, 5200), "zomato": _r(4.2, 2202)},
    "Mohali Walk": {"swiggy": _r(4.4, 40), "zomato": _r(4.1, 106)},
    "Mall of Jaipur": {"swiggy": _r(4.0, 117), "zomato": _r(4.1, 239)},
    "Karnal Haveli": {"swiggy": _r(3.1, 6), "zomato": _r(3.4, 16)},
    "Dhillon Plaza": {"swiggy": _r(4.0, 44), "zomato": _r(4.3, 148)},
    "Kharar": {"swiggy": _r(4.2, 57), "zomato": _r(4.2, 93)},
    "Panchkula": {"swiggy": _r(4.1, 52), "zomato": _r(4.3, 145)},
    "Sector 24": {"swiggy": _r(4.3, 60), "zomato": _r(4.2, 209)},
}

# No Google storefront ratings data has been provided yet — every store
# shows as not-yet-rated for Google until a snapshot is pasted here,
# same shape as RATINGS_BY_DISPLAY_NAME's swiggy/zomato entries.
GOOGLE_BY_DISPLAY_NAME = {}

_EMPTY_RATING = {"swiggy": _r(None, None), "zomato": _r(None, None)}


def ratings_for(display_name):
    base = RATINGS_BY_DISPLAY_NAME.get(display_name, _EMPTY_RATING)
    return {**base, "google": GOOGLE_BY_DISPLAY_NAME.get(display_name, _r(None, None))}
