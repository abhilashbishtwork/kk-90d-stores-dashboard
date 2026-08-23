"""Normalize `orders_state_transitions.cancelled_reason` /
`cancellation_message` into a short, presentable label.

Real data is messy: `cancelled_reason` is truncated to ~30 characters
by an upstream system (e.g. " because the restaurant is now" instead
of the full sentence), while `cancellation_message` usually carries the
full text but is sometimes blank. Aggregator-specific boilerplate
("reject-Order rejected due to 'X'", long Swiggy apology paragraphs)
needs pattern-matching to extract the actual reason rather than
displaying a wall of text or a truncated fragment.
"""

import re

_REJECT_QUOTED = re.compile(r"^reject-Order rejected due to '(.+)'$")
_STAFF_UPDATED = re.compile(r"^Reason: (.+?)\. Updated By ", re.IGNORECASE)

_SWIGGY_PATTERNS = [
    (re.compile(r"ordered item\(s\) are now out of stock"), "Item out of stock (Swiggy)"),
    (re.compile(r"restaurant is now closed and couldn'?t service"), "Restaurant closed (Swiggy)"),
    (re.compile(r"restaurant is closed; we apologise"), "Restaurant closed (Swiggy)"),
    (re.compile(r"order was running late"), "Order running late (Swiggy)"),
    (re.compile(r"significant delay in your order"), "Order running late (Swiggy)"),
    (re.compile(r"could not confirm the order due to a technical issue"), "Restaurant could not confirm (Swiggy)"),
    (re.compile(r"delivery partner faced an emergency"), "Delivery partner issue (Swiggy)"),
]

_REASON_CODE_LABELS = {
    "item_out_of_stock": "Item out of stock",
    "store_closed": "Store closed",
    "store_busy": "Store busy",
}


def normalize_reason(cancelled_reason, cancellation_message):
    # Real export data carries literal backslash-escaped quotes
    # (upstream JSON-escaping that was never unescaped) — normalize
    # before pattern matching so `\'` and `'` are treated the same.
    message = (cancellation_message or "").strip().replace("\\'", "'")
    reason = (cancelled_reason or "").strip()

    if message == "Order cancelled by Swiggy":
        return "Cancelled by Swiggy"

    match = _REJECT_QUOTED.match(message)
    if match:
        return match.group(1)

    match = _STAFF_UPDATED.match(message)
    if match:
        return match.group(1)

    for pattern, label in _SWIGGY_PATTERNS:
        if pattern.search(message):
            return label

    if message.isdigit():
        return f"Other (code {message})"

    if not message:
        if reason in _REASON_CODE_LABELS:
            return _REASON_CODE_LABELS[reason]
        if reason.isdigit():
            return f"Other (code {reason})"
        if not reason:
            return "Not specified"

    return message or "Not specified"
