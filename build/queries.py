"""Pure SQL-string builders for the KK 90-day-window dashboard's
ClickHouse pulls. No network calls here — these functions only build
query text so they can be unit tested without a live database.
"""

BRAND_ID = 95469015


def _store_list_sql(store_names):
    return ", ".join("'" + name.replace("'", "''") + "'" for name in store_names)


def build_online_history_query():
    """Full lifetime first/last order date per online store_name, for the
    brand — the input to `rename_guard.resolve_new_stores`. Deliberately
    unscoped by date or store: the rename guard needs a candidate's full
    history to walk back through any rename chain."""
    return f"""
        SELECT
            store_name AS store_name,
            min(toDate(created_at_ist)) AS first_seen,
            max(toDate(created_at_ist)) AS last_seen
        FROM orders
        WHERE brand_id = {BRAND_ID}
          AND channel IN ('swiggy', 'zomato', 'ownly')
        GROUP BY store_name
        FORMAT TabSeparatedWithNames
    """.strip()


def build_any_channel_history_query():
    """Full lifetime first/last order date per store_name, across every
    channel including POS/offline. Used to catch stores that have
    physically opened (taking dine-in orders) but have no online order
    yet — invisible to `build_online_history_query` alone, but still a
    genuine launch the ground team wants to see, even at zero online
    revenue."""
    return f"""
        SELECT
            store_name AS store_name,
            min(toDate(created_at_ist)) AS first_seen,
            max(toDate(created_at_ist)) AS last_seen
        FROM orders
        WHERE brand_id = {BRAND_ID}
        GROUP BY store_name
        FORMAT TabSeparatedWithNames
    """.strip()


def build_revenue_query(store_names, start_date, end_date):
    stores_sql = _store_list_sql(store_names)
    return f"""
        SELECT
            toDate(o.created_at_ist) AS order_date,
            o.store_name AS store_name,
            o.channel AS channel,
            sum(o.sub_total_amount - (o.discount - o.aggregator_discount) + o.charges) AS revenue,
            count(*) AS order_count
        FROM orders o
        LEFT JOIN (
            SELECT brand_id, order_id,
                   argMax(to_status, status_changed_at_ist) AS final_status
            FROM orders_state_transitions
            WHERE brand_id = {BRAND_ID}
            GROUP BY brand_id, order_id
        ) t ON t.brand_id = {BRAND_ID} AND t.order_id = o.id
        WHERE o.brand_id = {BRAND_ID}
          AND o.store_name IN ({stores_sql})
          AND o.channel IN ('swiggy', 'zomato', 'ownly')
          AND toDate(o.created_at_ist) >= toDate('{start_date}', 'Asia/Kolkata')
          AND toDate(o.created_at_ist) <= toDate('{end_date}', 'Asia/Kolkata')
          AND (t.final_status IS NULL OR t.final_status NOT IN ('Cancelled', 'customer_cancelled'))
        GROUP BY order_date, store_name, channel
        FORMAT TabSeparatedWithNames
    """.strip()


def build_ops_metrics_query(store_names, start_date, end_date):
    """Cancellation % and KPT (P80 Acknowledged -> Food Ready), same
    validated approach as the Pune/NCR dashboards. Scoped to
    swiggy/zomato only — Ownly has no comparable order-state pipeline."""
    stores_sql = _store_list_sql(store_names)
    return f"""
        WITH transitions_pivoted AS (
            SELECT
                brand_id,
                order_id,
                minIf(status_changed_at_ist, to_status = 'Acknowledged') AS ack_at,
                minIf(status_changed_at_ist, to_status = 'Food Ready') AS ready_at,
                argMax(to_status, status_changed_at_ist) AS final_status
            FROM orders_state_transitions
            WHERE brand_id = {BRAND_ID}
            GROUP BY brand_id, order_id
        ),
        per_order AS (
            SELECT
                toDate(o.created_at_ist) AS order_date,
                o.store_name AS store_name,
                o.channel AS channel,
                t.final_status AS final_status,
                if(t.ready_at > t.ack_at, dateDiff('minute', t.ack_at, t.ready_at), NULL) AS kpt_minutes
            FROM orders o
            LEFT JOIN transitions_pivoted t ON t.brand_id = {BRAND_ID} AND t.order_id = o.id
            WHERE o.brand_id = {BRAND_ID}
              AND o.store_name IN ({stores_sql})
              AND o.channel IN ('swiggy', 'zomato')
              AND toDate(o.created_at_ist) >= toDate('{start_date}', 'Asia/Kolkata')
              AND toDate(o.created_at_ist) <= toDate('{end_date}', 'Asia/Kolkata')
        )
        SELECT
            order_date,
            store_name,
            channel,
            count(*) AS total_orders,
            countIf(final_status IN ('Cancelled', 'customer_cancelled')) AS cancelled_orders,
            quantileIf(0.8)(kpt_minutes, kpt_minutes IS NOT NULL) AS kpt_p80_minutes
        FROM per_order
        GROUP BY order_date, store_name, channel
        FORMAT TabSeparatedWithNames
    """.strip()
