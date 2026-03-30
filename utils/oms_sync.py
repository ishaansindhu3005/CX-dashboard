"""
OMS MySQL integration — Short-Pick sync.

On page load, queries the OMS MySQL DB and upserts new short-pick records
into the local SQLite `short_pick_actions` table.

Config (environment variables):
    OMS_DB_HOST   — MySQL host (default: localhost)
    OMS_DB_PORT   — MySQL port (default: 3306)
    OMS_DB_USER   — MySQL user
    OMS_DB_PASS   — MySQL password
    OMS_DB_NAME   — MySQL database name

If the OMS DB is unreachable, returns 0 new records and logs a warning.
The dashboard continues to serve data from local SQLite (graceful degradation).
"""
import os
import streamlit as st
from db.connection import get_conn


def _oms_config() -> dict:
    return {
        "host":     os.getenv("OMS_DB_HOST", "localhost"),
        "port":     int(os.getenv("OMS_DB_PORT", "3306")),
        "user":     os.getenv("OMS_DB_USER", ""),
        "password": os.getenv("OMS_DB_PASS", ""),
        "database": os.getenv("OMS_DB_NAME", ""),
    }


def _oms_available() -> bool:
    cfg = _oms_config()
    return bool(cfg["user"] and cfg["database"])


@st.cache_data(ttl=300, show_spinner=False)
def sync_short_picks_from_oms() -> int:
    """
    Pull short-pick orders from OMS MySQL (last 30 days) and INSERT OR IGNORE
    into local `short_pick_actions` table.

    Returns the number of new rows inserted.
    If OMS is unavailable, returns 0.
    """
    if not _oms_available():
        return 0

    try:
        import mysql.connector  # type: ignore
    except ImportError:
        st.warning("mysql-connector-python not installed. Run: pip install mysql-connector-python")
        return 0

    cfg = _oms_config()
    try:
        oms = mysql.connector.connect(
            host=cfg["host"],
            port=cfg["port"],
            user=cfg["user"],
            password=cfg["password"],
            database=cfg["database"],
            connection_timeout=5,
        )
    except Exception as e:
        # OMS unreachable — fail silently, serve from local cache
        return 0

    try:
        cur = oms.cursor(dictionary=True)
        cur.execute("""
            SELECT
                o.order_id,
                o.customer_id,
                o.customer_phone,
                o.customer_name,
                o.order_amount,
                o.payment_method,
                o.store_code,
                GROUP_CONCAT(si.item_name SEPARATOR ', ')  AS short_items,
                GROUP_CONCAT(si.item_sku  SEPARATOR ', ')  AS short_skus,
                COUNT(si.id)                               AS short_item_count
            FROM orders o
            JOIN short_pick_items si ON si.order_id = o.order_id
            WHERE si.created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            GROUP BY o.order_id
        """)
        rows = cur.fetchall()
        cur.close()
        oms.close()
    except Exception:
        return 0

    if not rows:
        return 0

    local = get_conn()
    inserted = 0
    for row in rows:
        cur2 = local.execute(
            """
            INSERT OR IGNORE INTO short_pick_actions
                (order_id, customer_id, customer_phone, customer_name,
                 order_amount, payment_method, store_code,
                 short_items, short_skus, short_item_count)
            VALUES (?,?,?,?,?,?,?,?,?,?)
            """,
            (
                row["order_id"], row.get("customer_id"), row.get("customer_phone"),
                row.get("customer_name"), row.get("order_amount"), row.get("payment_method"),
                row.get("store_code"), row.get("short_items"), row.get("short_skus"),
                row.get("short_item_count", 0),
            ),
        )
        inserted += cur2.rowcount
    local.commit()
    local.close()
    return inserted
