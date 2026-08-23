from build.cancellation_reasons import normalize_reason


def test_extracts_reason_from_reject_quoted_message():
    assert normalize_reason("reject-Order rejected due to '", "reject-Order rejected due to 'Items out of stock'") == "Items out of stock"


def test_extracts_a_different_quoted_reason():
    assert normalize_reason("reject-Order rejected due to '", "reject-Order rejected due to 'Outlet closed'") == "Outlet closed"


def test_recognizes_swiggy_item_out_of_stock_apology_text():
    msg = " as the ordered item(s) are now out of stock at the restaurant. This happens rarely and we apologise for the inconvenience. Please visit the Swiggy app to order from a different restaurant"
    assert normalize_reason(" as the ordered item(s) are no", msg) == "Item out of stock (Swiggy)"


def test_recognizes_swiggy_restaurant_closed_apology_text():
    msg = " because the restaurant is now closed and couldn't service the order. We apologise for the inconvenience. Please visit the Swiggy app to order from a different restaurant"
    assert normalize_reason(" because the restaurant is now", msg) == "Restaurant closed (Swiggy)"


def test_recognizes_swiggy_restaurant_closed_apology_text_variant():
    msg = " because the restaurant is closed; we apologise for the inconvenience. Please use Swiggy app to place a new order."
    assert normalize_reason(" because the restaurant is clo", msg) == "Restaurant closed (Swiggy)"


def test_recognizes_swiggy_order_running_late_text():
    msg = " because your order was running late. We apologise for the inconvenience"
    assert normalize_reason(" because your order was runnin", msg) == "Order running late (Swiggy)"


def test_recognizes_plain_cancelled_by_swiggy_message():
    assert normalize_reason("Order cancelled by Swiggy", "Order cancelled by Swiggy") == "Cancelled by Swiggy"


def test_falls_back_to_reason_code_when_message_is_blank():
    assert normalize_reason("item_out_of_stock", "") == "Item out of stock"
    assert normalize_reason("store_closed", "") == "Store closed"
    assert normalize_reason("store_busy", "") == "Store busy"


def test_numeric_only_reason_becomes_other_with_code():
    assert normalize_reason("14", "14") == "Other (code 14)"


def test_blank_reason_and_message_is_not_specified():
    assert normalize_reason(None, None) == "Not specified"
    assert normalize_reason("", "") == "Not specified"


def test_unrecognized_message_is_returned_trimmed():
    assert normalize_reason("some_code", "A genuinely new reason text") == "A genuinely new reason text"


def test_handles_literal_backslash_escaped_quotes_in_reject_message():
    # Real ClickHouse export data contains literal backslashes before
    # apostrophes (upstream JSON-escaping never unescaped), not plain quotes.
    assert normalize_reason("x", "reject-Order rejected due to \\'Items out of stock\\'") == "Items out of stock"


def test_handles_backslash_escaped_apostrophe_in_swiggy_apology_text():
    msg = " because the restaurant is now closed and couldn\\'t service the order. We apologise for the inconvenience."
    assert normalize_reason("x", msg) == "Restaurant closed (Swiggy)"


def test_recognizes_significant_delay_apology_text():
    msg = " because there was a significant delay in your order. We apologise for the inconvenience."
    assert normalize_reason("x", msg) == "Order running late (Swiggy)"


def test_recognizes_technical_issue_apology_text():
    msg = " as the restaurant could not confirm the order due to a technical issue. This happens rarely and we apologise for the inconvenience"
    assert normalize_reason("x", msg) == "Restaurant could not confirm (Swiggy)"


def test_recognizes_delivery_partner_emergency_text():
    msg = " because the delivery partner faced an emergency and was unable to deliver your order post pickup from the restaurant."
    assert normalize_reason("x", msg) == "Delivery partner issue (Swiggy)"


def test_extracts_reason_from_staff_updated_by_format():
    assert normalize_reason("x", "Reason: Item Out Of Stock. Updated By Karthigeyan p") == "Item Out Of Stock"
    assert normalize_reason("x", "Reason: Store Closed. Updated By Noida sec141") == "Store Closed"
