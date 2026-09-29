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

# First Google storefront ratings pasted 2026-09-29 (same snapshot date
# as RATINGS_BY_DISPLAY_NAME). Coverage is partial — the source export
# only lists ~96 stores nationally (evidently ones with enough Google
# reviews to be listed), so most Pune stores and every brand-new store
# from this cycle (Medavakkam, 4 of the 5 Mumbai stores, SB Devanahalli)
# have no entry and simply show as not-yet-rated, same as before.
# "Inorbit Vashi" added separately from a user-supplied screenshot
# (not in the bulk export) since it's brand new (launched 2026-09-21).
GOOGLE_BY_DISPLAY_NAME = {
    "Mantri Mall": _r(4.2, 107),
    "SB Sarjapura": _r(4.6, 10),
    "Mohali Walk": _r(5.0, 19),
    "Nexus Elante Mall": _r(5.0, 1),
    "Mall of Jaipur": _r(5.0, 13),
    "GIP Mall": _r(5.0, 1),
    "Omaxe Chandni Chowk": _r(5.0, 1),
    "Pacific Tagore Garden Mall": _r(5.0, 14),
    "Amanora": _r(5.0, 58),
    "Baner": _r(4.9, 25),
    "Elpro Mall": _r(5.0, 48),
    "JM Road": _r(5.0, 45),
    "Niyati Plaza": _r(5.0, 51),
    "Inorbit Vashi": _r(5.0, 1),
    "Tribeca": _r(4.5, 44),
    "CP 67 Mall": _r(4.2, 25),
    "Karnal Haveli": _r(3.9, 16),
    "Dhillon Plaza": _r(4.9, 37),
    "Elan Miracle": _r(5.0, 1),
}

_EMPTY_RATING = {"swiggy": _r(None, None), "zomato": _r(None, None)}


def ratings_for(display_name):
    base = RATINGS_BY_DISPLAY_NAME.get(display_name, _EMPTY_RATING)
    return {**base, "google": GOOGLE_BY_DISPLAY_NAME.get(display_name, _r(None, None))}
