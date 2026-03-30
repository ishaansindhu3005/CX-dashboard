import os
import sqlite3

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "..", "ozi_cx.db"))


def get_conn():
    """
    Returns a SQLite connection with WAL mode and FK constraints.
    MySQL migration: replace sqlite3 with mysql.connector, swap ? → %s.
    """
    conn = sqlite3.connect(os.path.abspath(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Create all tables if they don't exist. Safe to call on every startup."""
    conn = get_conn()
    cur = conn.cursor()

    cur.executescript("""
        -- ── Stores ─────────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS stores (
            id          INTEGER PRIMARY KEY,
            name        TEXT NOT NULL,
            store_code  TEXT NOT NULL
        );

        -- ── CX Users (auth + identity) ─────────────────────────────────────────
        -- Primary user table used for login, RBAC, and call/task assignment.
        CREATE TABLE IF NOT EXISTS cx_users (
            id           INTEGER PRIMARY KEY,
            name         TEXT NOT NULL,
            email        TEXT,
            phone        TEXT,
            role         TEXT NOT NULL,   -- agent | cx_lead | wh_user | supervisor | admin
            is_active    INTEGER DEFAULT 1,
            is_available INTEGER DEFAULT 0
        );

        -- ── Role Permissions (RBAC) ─────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS role_permissions (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            role   TEXT NOT NULL,
            module TEXT NOT NULL,
            action TEXT NOT NULL,
            UNIQUE(role, module, action)
        );

        -- ── Returns ────────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS returns (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id             TEXT NOT NULL,
            customer_id          TEXT NOT NULL,
            customer_name        TEXT,
            customer_phone       TEXT,
            payment_method       TEXT NOT NULL DEFAULT 'prepaid',
            agent_id             INTEGER,
            type                 TEXT NOT NULL,
            source               TEXT NOT NULL,
            status               TEXT NOT NULL DEFAULT 'pending_action',
            refund_source        TEXT,
            reason               TEXT,
            spoken_to_customer   TEXT,
            pitched_exchange     TEXT,
            pickup_slot          TEXT,
            agent_notes          TEXT,
            rejection_reason     TEXT,
            store_id             INTEGER,
            pidge_tracking_id    TEXT,
            created_at           DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at           DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (agent_id)  REFERENCES cx_users(id),
            FOREIGN KEY (store_id)  REFERENCES stores(id)
        );

        -- ── Return Items ────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS return_items (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            return_id     INTEGER NOT NULL,
            item_name     TEXT NOT NULL,
            item_sku      TEXT,
            quantity      INTEGER DEFAULT 1,
            unit_price    REAL,
            return_amount REAL,
            FOREIGN KEY (return_id) REFERENCES returns(id)
        );

        -- ── Refunds ────────────────────────────────────────────────────────────
        -- status: pending_approval | pending | processed | completed | failed
        -- refund_type: return_app | admin_panel | chatbot | tnb | oos | cancelled_prepaid | manual
        CREATE TABLE IF NOT EXISTS refunds (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            return_id      INTEGER,
            order_id       TEXT NOT NULL,
            customer_id    TEXT NOT NULL,
            customer_phone TEXT,
            order_amount   REAL,
            amount         REAL NOT NULL,
            method         TEXT NOT NULL,
            refund_type    TEXT,
            coupon_code    TEXT,
            notes          TEXT,
            status         TEXT NOT NULL DEFAULT 'pending',
            triggered_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
            completed_at   DATETIME,
            FOREIGN KEY (return_id) REFERENCES returns(id)
        );

        -- ── CRM Calls ──────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS crm_calls (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id        TEXT NOT NULL UNIQUE,
            customer_id     TEXT,
            customer_phone  TEXT,
            customer_name   TEXT,
            order_amount    REAL,
            order_status    TEXT,
            new_repeat      TEXT,   -- new | repeat
            coupon_code     TEXT,
            assigned_to     INTEGER,
            call_status     TEXT DEFAULT 'pending',   -- pending | in_progress | completed
            reached_out     TEXT,                     -- yes | no | attempted
            drop_off_reason TEXT,
            reordered       TEXT,                     -- yes | no
            notes           TEXT,
            assigned_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
            started_at      DATETIME,
            completed_at    DATETIME,
            FOREIGN KEY (assigned_to) REFERENCES cx_users(id)
        );

        -- ── Short-Pick Actions ─────────────────────────────────────────────────
        -- Populated via OMS MySQL sync (see utils/oms_sync.py).
        CREATE TABLE IF NOT EXISTS short_pick_actions (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id          TEXT NOT NULL UNIQUE,
            customer_id       TEXT,
            customer_phone    TEXT,
            customer_name     TEXT,
            order_amount      REAL,
            payment_method    TEXT,
            store_code        TEXT,
            short_items       TEXT,    -- comma-separated item names from OMS
            short_skus        TEXT,    -- comma-separated SKUs
            short_item_count  INTEGER DEFAULT 0,
            assigned_to       INTEGER,
            action_status     TEXT DEFAULT 'pending',  -- pending | in_progress | completed
            reached_out       TEXT,
            customer_response TEXT,
            resolution        TEXT,
            notes             TEXT,
            synced_at         DATETIME DEFAULT CURRENT_TIMESTAMP,
            started_at        DATETIME,
            completed_at      DATETIME,
            FOREIGN KEY (assigned_to) REFERENCES cx_users(id)
        );
    """)
    conn.commit()

    # ── Migrate refunds table — add new columns if they don't exist ────────────
    existing = {row[1] for row in cur.execute("PRAGMA table_info(refunds)").fetchall()}
    migrations = [
        ("customer_phone", "TEXT"),
        ("order_amount",   "REAL"),
        ("refund_type",    "TEXT"),
        ("coupon_code",    "TEXT"),
        ("notes",          "TEXT"),
    ]
    for col, col_type in migrations:
        if col not in existing:
            cur.execute(f"ALTER TABLE refunds ADD COLUMN {col} {col_type}")

    # Make return_id nullable on existing DBs (SQLite can't ALTER COLUMN, skip — already nullable in new schema)
    conn.commit()
    conn.close()
