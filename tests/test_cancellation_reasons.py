from build.cancellation_reasons import normalize_reason, caused_by_for_reason


def test_merges_all_out_of_stock_variants_into_one_category():
    # Real data has this same underlying reason under wildly different
    # spellings/casings/sources — they must all collapse to one label.
    assert normalize_reason("x", "reject-Order rejected due to 'Items out of stock'") == "Item out of stock"
    assert normalize_reason("x", "reject-Order rejected due to \\'Item Out Of Stock\\'") == "Item out of stock"
    assert normalize_reason("item_out_of_stock", "") == "Item out of stock"
    assert normalize_reason("x", "Reason: Item Out Of Stock. Updated By Karthigeyan p") == "Item out of stock"
    msg = " as the ordered item(s) are now out of stock at the restaurant. This happens rarely and we apologise for the inconvenience. Please visit the Swiggy app to order from a different restaurant"
    assert normalize_reason("x", msg) == "Item out of stock"


def test_merges_all_restaurant_closed_variants_into_one_category():
    assert normalize_reason("x", "reject-Order rejected due to 'Outlet closed'") == "Restaurant closed"
    assert normalize_reason("store_closed", "") == "Restaurant closed"
    assert normalize_reason("x", "Reason: Store Closed. Updated By Noida sec141") == "Restaurant closed"
    msg = " because the restaurant is now closed and couldn\\'t service the order. We apologise for the inconvenience."
    assert normalize_reason("x", msg) == "Restaurant closed"
    msg2 = " because the restaurant is closed; we apologise for the inconvenience. Please use Swiggy app to place a new order."
    assert normalize_reason("x", msg2) == "Restaurant closed"
    msg3 = " as the restaurant could not confirm the order due to a technical issue. This happens rarely and we apologise for the inconvenience"
    assert normalize_reason("x", msg3) == "Restaurant closed"


def test_merges_order_delay_variants():
    msg = " because your order was running late. We apologise for the inconvenience"
    assert normalize_reason("x", msg) == "Order delayed"
    msg2 = " because there was a significant delay in your order. We apologise for the inconvenience."
    assert normalize_reason("x", msg2) == "Order delayed"


def test_merges_customer_cancellation_variants():
    assert normalize_reason("x", "reject-Order rejected due to 'Customer Cancellation'") == "Customer cancelled"
    assert normalize_reason("x", "reject-Order rejected due to 'Customer cancellation due to delay'") == "Customer cancelled"
    assert normalize_reason("x", "Customer cancellation") == "Customer cancelled"


def test_merges_store_busy_variants():
    assert normalize_reason("x", "reject-Order rejected due to 'Kitchen is full'") == "Store busy"
    assert normalize_reason("store_busy", "") == "Store busy"


def test_merges_delivery_partner_variants():
    assert normalize_reason("x", "reject-Order rejected due to 'Delivery partner cancellation'") == "Delivery partner issue"
    msg = " because the delivery partner faced an emergency and was unable to deliver your order post pickup from the restaurant."
    assert normalize_reason("x", msg) == "Delivery partner issue"


def test_wrong_merchant_address():
    assert normalize_reason("x", "reject-Order rejected due to 'Wrong merchant address'") == "Wrong merchant address"


def test_wrong_customer_address_is_a_customer_side_reason():
    assert normalize_reason("x", "reject-Order rejected due to 'Wrong customer address'") == "Wrong customer address"
    assert caused_by_for_reason("Wrong customer address") == "Customer"


def test_platform_order_modification_counts_as_cancelled_by_platform():
    assert normalize_reason("unspecified", "Swiggy Order Modification") == "Cancelled by platform"


def test_outlet_not_open_yet_is_restaurant_closed():
    assert normalize_reason("x", "reject-Order rejected due to 'Outlet not open yet'") == "Restaurant closed"


def test_merchant_technical_issue():
    assert normalize_reason("x", "reject-Order rejected due to 'Merchant device or electricity issue'") == "Merchant technical issue"


def test_generic_cancelled_by_platform_message():
    assert normalize_reason("Order cancelled by Swiggy", "Order cancelled by Swiggy") == "Cancelled by platform"


def test_numeric_only_reason_becomes_other_with_code():
    assert normalize_reason("14", "14") == "Other (code 14)"


def test_blank_reason_and_message_is_not_specified():
    assert normalize_reason(None, None) == "Not specified"
    assert normalize_reason("", "") == "Not specified"


def test_unrecognized_message_is_returned_trimmed():
    assert normalize_reason("some_code", "A genuinely new reason text") == "A genuinely new reason text"


def test_item_out_of_stock_is_caused_by_restaurant_not_the_aggregator():
    # This is the actual bug report: the raw cancelled_by field says
    # "Aggregator" (whichever app processed the cancel) even when the
    # underlying reason is squarely a restaurant-side stock problem.
    assert caused_by_for_reason("Item out of stock") == "Restaurant"


def test_restaurant_side_reasons_are_caused_by_restaurant():
    assert caused_by_for_reason("Restaurant closed") == "Restaurant"
    assert caused_by_for_reason("Store busy") == "Restaurant"
    assert caused_by_for_reason("Merchant technical issue") == "Restaurant"
    assert caused_by_for_reason("Wrong merchant address") == "Restaurant"
    assert caused_by_for_reason("Order delayed") == "Restaurant"


def test_customer_cancelled_is_caused_by_customer():
    assert caused_by_for_reason("Customer cancelled") == "Customer"


def test_delivery_partner_issue_is_caused_by_delivery_partner():
    assert caused_by_for_reason("Delivery partner issue") == "Delivery partner"


def test_generic_platform_cancellation_is_caused_by_platform():
    assert caused_by_for_reason("Cancelled by platform") == "Platform"


def test_unknown_reason_falls_back_to_other():
    assert caused_by_for_reason("Not specified") == "Unknown"
    assert caused_by_for_reason("Some new reason we've never categorized") == "Other"
