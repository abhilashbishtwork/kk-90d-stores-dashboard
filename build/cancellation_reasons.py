"""Normalize `orders_state_transitions.cancelled_reason` /
`cancellation_message` into one of a small set of canonical reason
categories, and map each category to who actually caused it.

Real data is extremely messy: the same underlying reason ("this item
ran out") shows up as a reason code (`item_out_of_stock`), a quoted
rejection ("reject-Order rejected due to 'Items out of stock'"), a
staff-entered note ("Reason: Item Out Of Stock. Updated By ..."), and a
full Swiggy customer-apology paragraph — different casing and wording
every time. Rather than hard-coding every literal variant, we extract
the underlying text (unwrapping quoted/staff-note wrappers) and then
match on a small set of case-insensitive key phrases, so all variants
of the same real-world reason collapse to one label.

`cancelled_by` (aggregator vs merchant app) reflects which system
executed the cancellation transition, NOT whose fault it was — e.g. a
restaurant marking an item out of stock in the Swiggy app still shows
up as "cancelled by Swiggy". Use `caused_by_for_reason()` instead,
which derives actual fault from the canonical reason.
"""

import re

_REJECT_QUOTED = re.compile(r"^reject-Order rejected due to '(.+)'$")
_STAFF_UPDATED = re.compile(r"^Reason: (.+?)\. Updated By ", re.IGNORECASE)

_PHRASE_RULES = [
    (re.compile(r"out of stock", re.IGNORECASE), "Item out of stock"),
    (re.compile(r"could not confirm|restaurant is (now )?closed|outlet closed|outlet not open|store[ _]closed", re.IGNORECASE), "Restaurant closed"),
    (re.compile(r"running late|significant delay", re.IGNORECASE), "Order delayed"),
    (re.compile(r"wrong customer address", re.IGNORECASE), "Wrong customer address"),
    (re.compile(r"customer[ _]?cancellation|^customer\b", re.IGNORECASE), "Customer cancelled"),
    (re.compile(r"kitchen is full|kitchen[ _]full|store[ _]busy", re.IGNORECASE), "Store busy"),
    (re.compile(r"delivery partner", re.IGNORECASE), "Delivery partner issue"),
    (re.compile(r"wrong merchant address", re.IGNORECASE), "Wrong merchant address"),
    (re.compile(r"device or electricity", re.IGNORECASE), "Merchant technical issue"),
    (re.compile(r"cancelled by swiggy|cancelled by zomato|order modification", re.IGNORECASE), "Cancelled by platform"),
]

CAUSED_BY_MAP = {
    "Item out of stock": "Restaurant",
    "Restaurant closed": "Restaurant",
    "Store busy": "Restaurant",
    "Merchant technical issue": "Restaurant",
    "Wrong merchant address": "Restaurant",
    "Order delayed": "Restaurant",
    "Customer cancelled": "Customer",
    "Wrong customer address": "Customer",
    "Delivery partner issue": "Delivery partner",
    "Cancelled by platform": "Platform",
    "Not specified": "Unknown",
}


def _match_phrase(text):
    for pattern, label in _PHRASE_RULES:
        if pattern.search(text):
            return label
    return None


def normalize_reason(cancelled_reason, cancellation_message):
    message = (cancellation_message or "").strip().replace("\\'", "'")
    reason = (cancelled_reason or "").strip()

    match = _REJECT_QUOTED.match(message)
    if match:
        message = match.group(1).strip()

    match = _STAFF_UPDATED.match(message)
    if match:
        message = match.group(1).strip()

    label = _match_phrase(message)
    if label:
        return label

    if message.isdigit():
        return f"Other (code {message})"

    if not message:
        label = _match_phrase(reason.replace("_", " "))
        if label:
            return label
        if reason.isdigit():
            return f"Other (code {reason})"
        if not reason:
            return "Not specified"
        return reason.replace("_", " ").strip()

    return message


def caused_by_for_reason(reason):
    return CAUSED_BY_MAP.get(reason, "Other")
