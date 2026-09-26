"""Derive a display city from a KK ClickHouse `store_name`.

The 90-day roster is computed dynamically (see `rename_guard.py`), so
there is no hardcoded store list to attach a city to. Instead we read the
city off the store_name's own prefix convention, which is consistent
across every KK store_name observed in ClickHouse.
"""

PREFIX_TO_CITY = {
    "PNQ": "Pune",
    "DEL": "NCR",
    "NOI": "NCR",
    "GGN": "NCR",
    "GZB": "NCR",
    "FDB": "NCR",
    "BLR": "Bengaluru",
    "BOM": "Mumbai",
    "MAA": "Chennai",
    "HYD": "Hyderabad",
    "JAI": "Jaipur",
    "IXC": "Chandigarh Tricity",
}

MULTI_WORD_PREFIXES = {
    "greater noida": "NCR",
    "noida": "NCR",
}

# Navi Mumbai stores sometimes carry a "PNQ" (Pune) prefix in ClickHouse
# (e.g. "PNQ KK Nerul"); the locality wins over the prefix.
MUMBAI_LOCALITIES = {"nerul", "kharghar", "vashi", "airoli", "panvel", "belapur", "sanpada", "ghansoli", "seawoods", "ulwe", "kamothe"}

UNCLASSIFIED = "Unclassified"


def city_for(store_name):
    lowered = store_name.strip().lower()
    if MUMBAI_LOCALITIES & set(lowered.replace(",", " ").split()):
        return "Mumbai"
    for prefix, city in MULTI_WORD_PREFIXES.items():
        if lowered.startswith(prefix):
            return city

    first_word = lowered.split(" ")[0].upper()
    return PREFIX_TO_CITY.get(first_word, UNCLASSIFIED)


_DISPLAY_FILLER = {"kk", "online", "pos", "offline", "krispy", "kripsy", "kreme", "ncr", "-"}


def display_name_for(store_name):
    tokens = store_name.replace(",", " ").split()

    lowered = [t.lower() for t in tokens]
    if lowered[:2] == ["greater", "noida"]:
        tokens = tokens[2:]
    elif lowered[0] == "noida":
        tokens = tokens[1:]
    elif tokens[0].upper() in PREFIX_TO_CITY:
        tokens = tokens[1:]

    cleaned = [t for t in tokens if t.lower() not in _DISPLAY_FILLER]
    return " ".join(cleaned).strip(" -,")
