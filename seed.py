"""
Seed dummy data into ozi_cx.db.
Run once: python seed.py
Safe to re-run — drops and recreates all data.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from db.connection import init_db, get_conn
import uuid
from datetime import datetime, timedelta
import random

# ── Master data ───────────────────────────────────────────────────────────────

STORES = [
    (11, "Sector 65",   "S65"),
    (12, "DLF Phase 1", "DLF1"),
    (13, "Sohna Road",  "SRD"),
    (14, "Manesar",     "MNS"),
]

# cx_users: (id, name, email, phone, role, is_active, is_available)
CX_USERS = [
    (1, "Priya Nair",     "priya@ozi.in",   "+91 98100 11111", "agent",      1, 0),
    (2, "Arjun Mehta",    "arjun@ozi.in",   "+91 98100 22222", "agent",      1, 0),
    (3, "Bhagwana Singh", "bhagwana@ozi.in","+91 98100 33333", "cx_lead",    1, 0),
    (4, "Kusharg Sharma", "kusharg@ozi.in", "+91 98100 44444", "wh_user",    1, 0),
    (5, "Vaibhav Gupta",  "vaibhav@ozi.in", "+91 98100 55555", "supervisor", 1, 0),
    (6, "Ishaan Sindhu",  "ishaan@ozi.in",  "+91 98100 66666", "admin",      1, 0),
]

PRODUCTS = [
    ("Barbie Doctor Doll",             "100000553001", 1499, 924.25),
    ("Philips Avent Breast Pump",      "100000212001", 7995, 3486.58),
    ("Skillmatics Dot It! Magnets",    "100000271001",  899,  699.00),
    ("R for Rabbit Silicone Bibs",     "100000167001",  396,  332.64),
    ("Pampers Premium Care Pants XL",  "100000131004", 1499, 1138.94),
    ("Mi Arcus Bow Headbands Pack",    "100000283001",  399,  766.00),
    ("KID1 Kanha Dhoti Set 6-12M",     "100000253002", 1099, 1099.00),
    ("Orange Sugar Co-ord Set 3-6M",   "100000240002",  849,  747.12),
    ("Hot Wheels Plymouth Superbird",  "100000569012",  179,  152.15),
    ("Avenir Puffy Sticker Set",       "100000347001",  399,  398.00),
    ("Sophie La Girafe Teether",       "100000187001", 2799, 2799.00),
    ("Chicco Liquid Cleanser 200ml",   "100000048001",  229,  229.00),
]

CUSTOMERS = [
    ("C001", "Priya Sharma",   "+91 98110 12345", "prepaid"),
    ("C002", "Arjun Malhotra", "+91 97300 54321", "prepaid"),
    ("C003", "Sneha Kapoor",   "+91 99990 11223", "cod"),
    ("C004", "Rahul Gupta",    "+91 98765 43210", "prepaid"),
    ("C005", "Meena Tiwari",   "+91 98001 67890", "prepaid"),
    ("C006", "Deepak Verma",   "+91 97112 34567", "cod"),
    ("C007", "Anita Joshi",    "+91 98200 11111", "prepaid"),
    ("C008", "Suresh Rao",     "+91 99887 66554", "prepaid"),
]

REASONS  = ["wrong_product", "damaged", "expired", "size_issue", "not_as_expected", "other"]
SOURCES  = ["app", "chatbot", "admin_panel"]
TYPES    = ["return", "exchange"]

# ── RBAC permissions ──────────────────────────────────────────────────────────

ROLE_PERMISSIONS = [
    # agent
    ("agent", "dashboard",   "view"),
    ("agent", "returns",     "view"),   ("agent", "returns",     "action"),  ("agent", "returns", "create"),
    ("agent", "refunds",     "view"),
    ("agent", "customers",   "view"),
    ("agent", "orders",      "view"),
    ("agent", "crm_calling", "view"),   ("agent", "crm_calling", "call"),
    ("agent", "short_picks", "view"),   ("agent", "short_picks", "action"),

    # cx_lead
    ("cx_lead", "dashboard",   "view"),
    ("cx_lead", "returns",     "view"),   ("cx_lead", "returns",     "action"),
    ("cx_lead", "returns",     "approve"),("cx_lead", "returns",     "reject"),  ("cx_lead", "returns", "create"),
    ("cx_lead", "refunds",     "view"),   ("cx_lead", "refunds",     "action"),
    ("cx_lead", "refunds",     "approve"),("cx_lead", "refunds",     "create"),
    ("cx_lead", "customers",   "view"),
    ("cx_lead", "orders",      "view"),
    ("cx_lead", "crm_calling", "view"),   ("cx_lead", "crm_calling", "call"),
    ("cx_lead", "short_picks", "view"),   ("cx_lead", "short_picks", "action"),

    # wh_user
    ("wh_user", "returns",     "view"),  ("wh_user", "returns",     "pickup"),
    ("wh_user", "refunds",     "view"),
    ("wh_user", "crm_calling", "view"),
    ("wh_user", "short_picks", "view"),

    # supervisor
    ("supervisor", "dashboard",   "view"),
    ("supervisor", "returns",     "view"),   ("supervisor", "returns",     "action"),
    ("supervisor", "returns",     "approve"),("supervisor", "returns",     "reject"),  ("supervisor", "returns", "create"),
    ("supervisor", "refunds",     "view"),   ("supervisor", "refunds",     "action"),
    ("supervisor", "refunds",     "approve"),("supervisor", "refunds",     "create"),
    ("supervisor", "customers",   "view"),
    ("supervisor", "orders",      "view"),
    ("supervisor", "crm_calling", "view"),   ("supervisor", "crm_calling", "call"),
    ("supervisor", "crm_calling", "reassign"),
    ("supervisor", "short_picks", "view"),   ("supervisor", "short_picks", "action"),
    ("supervisor", "short_picks", "reassign"),
    ("supervisor", "users",       "view"),

    # admin
    ("admin", "dashboard",   "view"),
    ("admin", "returns",     "view"),   ("admin", "returns",     "action"),
    ("admin", "returns",     "approve"),("admin", "returns",     "reject"),  ("admin", "returns", "create"),
    ("admin", "refunds",     "view"),   ("admin", "refunds",     "action"),
    ("admin", "refunds",     "approve"),("admin", "refunds",     "create"),  ("admin", "refunds", "override_amount"),
    ("admin", "customers",   "view"),
    ("admin", "orders",      "view"),
    ("admin", "crm_calling", "view"),   ("admin", "crm_calling", "call"),
    ("admin", "crm_calling", "reassign"),
    ("admin", "short_picks", "view"),   ("admin", "short_picks", "action"),
    ("admin", "short_picks", "reassign"),
    ("admin", "users",       "view"),   ("admin", "users",       "create"),
    ("admin", "users",       "edit"),   ("admin", "users",       "delete"),
    ("admin", "roles",       "view"),   ("admin", "roles",       "create"),
    ("admin", "roles",       "edit"),   ("admin", "roles",       "delete"),
]

# ── CRM call seed data ────────────────────────────────────────────────────────

CRM_STATUSES = ["rto_out_for_delivery", "rto_delivered", "cancelled", "failed", "undelivered", "pending"]
CRM_CUSTOMERS = [
    ("C011", "Neha Agarwal",  "+91 99001 10001", 1249.0, "new"),
    ("C012", "Rohan Kapoor",  "+91 99001 10002", 2499.0, "repeat"),
    ("C013", "Sunita Yadav",  "+91 99001 10003",  799.0, "new"),
    ("C014", "Mohit Sharma",  "+91 99001 10004", 3299.0, "repeat"),
    ("C015", "Kavya Nair",    "+91 99001 10005", 1899.0, "new"),
    ("C016", "Ajay Singh",    "+91 99001 10006",  649.0, "repeat"),
    ("C017", "Preeti Jain",   "+91 99001 10007", 4199.0, "new"),
    ("C018", "Sunil Kumar",   "+91 99001 10008", 1099.0, "repeat"),
    ("C019", "Pooja Mehta",   "+91 99001 10009", 2149.0, "new"),
    ("C020", "Vikas Gupta",   "+91 99001 10010",  999.0, "repeat"),
]
COUPON_CODES = ["OZI10", "BABY20", "FIRST50", None, None, "WELCOME15", None]

DROP_OFF_REASONS = [
    "cx_unavailable", "not_interested", "price_too_expensive",
    "bad_delivery", "forgot_coupon", "too_slow", "product_quality", "other"
]
CUSTOMER_RESPONSES  = ["Understood & Accepted", "Upset", "Wants Full Refund", "Wants Replacement", "No Response", "Other"]
RESOLUTIONS         = ["Refund Initiated", "Replacement Arranged", "Partial Refund", "Customer Cancelled", "No Action Needed", "Other"]

# ── Short-pick seed data ──────────────────────────────────────────────────────

SHORT_PICK_CUSTOMERS = [
    ("C021", "Ananya Roy",    "+91 98500 20001", 1599.0, "prepaid", "S65"),
    ("C022", "Tarun Bhatia",  "+91 98500 20002", 2299.0, "cod",     "DLF1"),
    ("C023", "Ritu Sharma",   "+91 98500 20003",  899.0, "prepaid", "SRD"),
    ("C024", "Amit Verma",    "+91 98500 20004", 3499.0, "prepaid", "MNS"),
    ("C025", "Sonia Kapoor",  "+91 98500 20005", 1299.0, "cod",     "S65"),
    ("C026", "Deepak Nair",   "+91 98500 20006", 4199.0, "prepaid", "DLF1"),
    ("C027", "Neelam Joshi",  "+91 98500 20007",  749.0, "prepaid", "SRD"),
    ("C028", "Rahul Mehta",   "+91 98500 20008", 1849.0, "cod",     "S65"),
    ("C029", "Preethi Iyer",  "+91 98500 20009", 2599.0, "prepaid", "DLF1"),
    ("C030", "Kartik Singh",  "+91 98500 20010",  999.0, "prepaid", "MNS"),
]

SHORT_ITEMS_POOL = [
    ("Pampers Premium Care XL", "100000131004"),
    ("Barbie Doctor Doll",       "100000553001"),
    ("R for Rabbit Bibs",        "100000167001"),
    ("Sophie La Girafe",         "100000187001"),
    ("Chicco Cleanser",          "100000048001"),
    ("Skillmatics Magnets",      "100000271001"),
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def random_dt(days_ago_max=14):
    delta = timedelta(
        days=random.randint(0, days_ago_max),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
    )
    return (datetime.now() - delta).strftime("%Y-%m-%d %H:%M:%S")


def pick_refund_source(payment_method, return_type):
    if return_type == "exchange":
        return None
    if payment_method == "cod":
        return "cod_wallet"
    return random.choice(["wallet", "source_refund"])


def seed():
    init_db()
    conn = get_conn()

    # ── Wipe existing data ────────────────────────────────────────────────────
    for tbl in (
        "short_pick_actions", "crm_calls", "role_permissions",
        "refunds", "return_items", "returns", "cx_users", "stores",
    ):
        conn.execute(f"DELETE FROM {tbl}")
    conn.commit()

    # ── Stores ────────────────────────────────────────────────────────────────
    conn.executemany("INSERT INTO stores (id, name, store_code) VALUES (?,?,?)", STORES)

    # ── CX Users ─────────────────────────────────────────────────────────────
    conn.executemany(
        "INSERT INTO cx_users (id, name, email, phone, role, is_active, is_available) VALUES (?,?,?,?,?,?,?)",
        CX_USERS,
    )

    # ── Role Permissions ──────────────────────────────────────────────────────
    conn.executemany(
        "INSERT OR IGNORE INTO role_permissions (role, module, action) VALUES (?,?,?)",
        ROLE_PERMISSIONS,
    )
    conn.commit()

    # ── Returns ───────────────────────────────────────────────────────────────
    returns_inserted = 0
    refunds_inserted = 0

    def insert_return(order_id, customer, ret_type, source, status,
                      agent_id=None, store_id=None, days_ago=3,
                      spoken=None, pitched=None, reason=None,
                      refund_src=None, pickup_slot=None, notes=None,
                      rejection_reason=None, pidge_id=None, items=None):
        nonlocal returns_inserted, refunds_inserted
        cust_id, cust_name, cust_phone, payment_method = customer
        created = random_dt(days_ago)
        cur = conn.execute(
            """
            INSERT INTO returns (
                order_id, customer_id, customer_name, customer_phone,
                payment_method, agent_id, type, source, status,
                refund_source, reason, spoken_to_customer, pitched_exchange,
                pickup_slot, agent_notes, rejection_reason,
                store_id, pidge_tracking_id, created_at, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                order_id, cust_id, cust_name, cust_phone,
                payment_method, agent_id, ret_type, source, status,
                refund_src, reason, spoken, pitched,
                pickup_slot, notes, rejection_reason,
                store_id, pidge_id, created, created,
            )
        )
        rid = cur.lastrowid
        returns_inserted += 1
        items = items or [random.choice(PRODUCTS)]
        for item in items:
            name, sku, price, ret_amt = item
            conn.execute(
                "INSERT INTO return_items (return_id, item_name, item_sku, quantity, unit_price, return_amount) VALUES (?,?,?,1,?,?)",
                (rid, name, sku, price, ret_amt),
            )
        if status == "completed" and ret_type == "return":
            total_amt = sum(i[3] for i in items)
            method = refund_src or "wallet"
            conn.execute(
                "INSERT INTO refunds (return_id, order_id, customer_id, amount, method, status, triggered_at) VALUES (?,?,?,?,?,'pending',?)",
                (rid, order_id, cust_id, total_amt, method, created),
            )
            refunds_inserted += 1
        return rid

    # 5 × pending_action
    insert_return("ORD-20410", CUSTOMERS[0], "return",   "app",         "pending_action", agent_id=1, days_ago=0, items=[PRODUCTS[0]])
    insert_return("ORD-20552", CUSTOMERS[1], "exchange", "chatbot",     "pending_action", agent_id=1, days_ago=0, items=[PRODUCTS[6]])
    insert_return("ORD-20613", CUSTOMERS[2], "return",   "app",         "pending_action", agent_id=2, days_ago=1, items=[PRODUCTS[4]])
    insert_return("ORD-20784", CUSTOMERS[3], "return",   "admin_panel", "pending_action", agent_id=2, days_ago=1, items=[PRODUCTS[1]])
    insert_return("ORD-20830", CUSTOMERS[4], "exchange", "chatbot",     "pending_action", agent_id=1, days_ago=2, items=[PRODUCTS[9]])

    # 5 × pending_approval
    insert_return("ORD-20121", CUSTOMERS[5], "return",   "app",     "pending_approval", agent_id=1, days_ago=2,
                  spoken="yes", pitched="no",       reason="wrong_product",   refund_src="wallet",        pickup_slot="26 Mar 2026, 10AM–12PM", items=[PRODUCTS[7]])
    insert_return("ORD-20234", CUSTOMERS[6], "exchange", "chatbot", "pending_approval", agent_id=2, days_ago=3,
                  spoken="yes", pitched="yes",      reason="size_issue",       refund_src=None,            pickup_slot="27 Mar 2026, 2PM–4PM",   items=[PRODUCTS[5]])
    insert_return("ORD-20345", CUSTOMERS[7], "return",   "app",     "pending_approval", agent_id=1, days_ago=3,
                  spoken="attempted", pitched="no", reason="damaged",          refund_src="source_refund", pickup_slot="27 Mar 2026, 10AM–12PM", items=[PRODUCTS[2]])
    insert_return("ORD-20456", CUSTOMERS[0], "return",   "app",     "pending_approval", agent_id=2, days_ago=4,
                  spoken="yes", pitched="no",       reason="not_as_expected",  refund_src="wallet",        pickup_slot="28 Mar 2026, 4PM–6PM",   items=[PRODUCTS[10]])
    insert_return("ORD-20567", CUSTOMERS[1], "exchange", "chatbot", "pending_approval", agent_id=1, days_ago=4,
                  spoken="yes", pitched="yes",      reason="size_issue",       refund_src=None,            pickup_slot="28 Mar 2026, 12PM–2PM",  items=[PRODUCTS[6], PRODUCTS[9]])

    # 5 × pending_pickup
    insert_return("ORD-20678", CUSTOMERS[2], "return",   "app",         "pending_pickup", agent_id=1, days_ago=4,
                  spoken="yes", pitched="no",       reason="wrong_product",  refund_src="wallet",        pickup_slot="25 Mar 2026, 10AM–12PM", items=[PRODUCTS[3]])
    insert_return("ORD-20789", CUSTOMERS[3], "exchange", "chatbot",     "pending_pickup", agent_id=2, days_ago=5,
                  spoken="yes", pitched="yes",      reason="size_issue",     refund_src=None,            pickup_slot="25 Mar 2026, 2PM–4PM",   items=[PRODUCTS[7]])
    insert_return("ORD-20890", CUSTOMERS[4], "return",   "app",         "pending_pickup", agent_id=1, days_ago=5,
                  spoken="attempted", pitched="no", reason="damaged",        refund_src="source_refund", pickup_slot="26 Mar 2026, 10AM–12PM", items=[PRODUCTS[0], PRODUCTS[2]])
    insert_return("ORD-20901", CUSTOMERS[5], "return",   "app",         "pending_pickup", agent_id=2, days_ago=6,
                  spoken="yes", pitched="no",       reason="expired",        refund_src="wallet",        pickup_slot="26 Mar 2026, 4PM–6PM",   items=[PRODUCTS[11]])
    insert_return("ORD-21012", CUSTOMERS[6], "exchange", "admin_panel", "pending_pickup", agent_id=2, days_ago=6,
                  spoken="yes", pitched="yes",      reason="not_as_expected",refund_src=None,            pickup_slot="27 Mar 2026, 10AM–12PM", items=[PRODUCTS[5]])

    # 4 × out_for_pickup
    insert_return("ORD-21123", CUSTOMERS[7], "return",   "app",     "out_for_pickup", agent_id=1, days_ago=6,
                  spoken="yes", pitched="no",       reason="wrong_product",  refund_src="wallet",        pickup_slot="24 Mar 2026, 10AM–12PM",
                  store_id=11, pidge_id=f"PIDGE-{uuid.uuid4().hex[:8].upper()}", items=[PRODUCTS[1]])
    insert_return("ORD-21234", CUSTOMERS[0], "exchange", "chatbot", "out_for_pickup", agent_id=2, days_ago=7,
                  spoken="yes", pitched="yes",      reason="size_issue",     refund_src=None,            pickup_slot="24 Mar 2026, 2PM–4PM",
                  store_id=12, pidge_id=f"PIDGE-{uuid.uuid4().hex[:8].upper()}", items=[PRODUCTS[6]])
    insert_return("ORD-21345", CUSTOMERS[1], "return",   "app",     "out_for_pickup", agent_id=1, days_ago=8,
                  spoken="attempted", pitched="no", reason="damaged",        refund_src="source_refund", pickup_slot="23 Mar 2026, 10AM–12PM",
                  store_id=11, pidge_id=f"PIDGE-{uuid.uuid4().hex[:8].upper()}", items=[PRODUCTS[4]])
    insert_return("ORD-21456", CUSTOMERS[2], "return",   "app",     "out_for_pickup", agent_id=2, days_ago=9,
                  spoken="yes", pitched="no",       reason="not_as_expected",refund_src="wallet",        pickup_slot="22 Mar 2026, 4PM–6PM",
                  store_id=13, pidge_id=f"PIDGE-{uuid.uuid4().hex[:8].upper()}", items=[PRODUCTS[8]])

    # 4 × completed
    insert_return("ORD-21567", CUSTOMERS[3], "return",   "app",     "completed", agent_id=1, days_ago=10,
                  spoken="yes", pitched="no",       reason="wrong_product",  refund_src="wallet",        pickup_slot="20 Mar 2026, 10AM–12PM",
                  store_id=11, pidge_id=f"PIDGE-{uuid.uuid4().hex[:8].upper()}", items=[PRODUCTS[0]])
    insert_return("ORD-21678", CUSTOMERS[4], "exchange", "chatbot", "completed", agent_id=2, days_ago=11,
                  spoken="yes", pitched="yes",      reason="size_issue",     refund_src=None,            pickup_slot="19 Mar 2026, 2PM–4PM",
                  store_id=12, pidge_id=f"PIDGE-{uuid.uuid4().hex[:8].upper()}", items=[PRODUCTS[7]])
    insert_return("ORD-21789", CUSTOMERS[5], "return",   "app",     "completed", agent_id=1, days_ago=12,
                  spoken="yes", pitched="no",       reason="damaged",        refund_src="source_refund", pickup_slot="18 Mar 2026, 10AM–12PM",
                  store_id=11, pidge_id=f"PIDGE-{uuid.uuid4().hex[:8].upper()}", items=[PRODUCTS[1]])
    insert_return("ORD-21890", CUSTOMERS[6], "return",   "chatbot", "completed", agent_id=2, days_ago=13,
                  spoken="attempted", pitched="no", reason="not_as_expected",refund_src="wallet",        pickup_slot="17 Mar 2026, 4PM–6PM",
                  store_id=13, pidge_id=f"PIDGE-{uuid.uuid4().hex[:8].upper()}", items=[PRODUCTS[10]])

    # 2 × cancelled
    insert_return("ORD-22001", CUSTOMERS[7], "return",   "app",     "cancelled", agent_id=1, days_ago=7,
                  spoken="yes", pitched="no",  reason="size_issue",  refund_src="wallet",
                  rejection_reason="Customer agreed to keep the product after exchange explanation.",
                  items=[PRODUCTS[5]])
    insert_return("ORD-22112", CUSTOMERS[0], "exchange", "chatbot", "cancelled", agent_id=2, days_ago=9,
                  spoken="yes", pitched="yes", reason="other",       refund_src=None,
                  rejection_reason="Duplicate request — already processed in admin panel.",
                  items=[PRODUCTS[3]])

    conn.commit()

    # ── Manual & extra refunds (all statuses) ─────────────────────────────────
    extra_refunds = [
        # (order_id, customer_id, customer_phone, order_amount, amount, method, refund_type, coupon, notes, status)
        # pending_approval (6)
        ("ORD-20410", "C001", "+91 98110 12345", 1499.0,  924.0, "wallet",        "return_app",        None,       "Customer confirmed return.",          "pending_approval"),
        ("ORD-20552", "C002", "+91 97300 54321", 2499.0, 1099.0, "source_refund", "return_app",        None,       "Exchange declined by customer.",      "pending_approval"),
        ("ORD-20613", "C003", "+91 99990 11223",  899.0,  699.0, "cod_wallet",    "return_app",        None,       "COD order — wallet credit.",          "pending_approval"),
        ("ORD-25001", "C005", "+91 98001 67890",  449.0,  449.0, "wallet",        "oos",               None,       "Item went OOS — full refund.",        "pending_approval"),
        ("ORD-25002", "C006", "+91 97112 34567", 1299.0,  799.0, "source_refund", "admin_panel",       "BACK15",   "Admin initiated return refund.",      "pending_approval"),
        ("ORD-25003", "C007", "+91 98200 11111",  599.0,  549.0, "cod_wallet",    "chatbot",           None,       "Chatbot-initiated COD refund.",       "pending_approval"),
        # pending (8)
        ("ORD-20784", "C004", "+91 98765 43210", 7995.0, 3486.0, "wallet",        "admin_panel",       "BABY20",   "Initiated via admin.",                "pending"),
        ("ORD-20830", "C005", "+91 98001 67890", 1499.0,  766.0, "source_refund", "chatbot",           None,       "Chatbot initiated refund.",           "pending"),
        ("ORD-20121", "C006", "+91 97112 34567",  396.0,  332.0, "wallet",        "return_app",        None,       None,                                  "pending"),
        ("ORD-25004", "C008", "+91 99887 66554", 3299.0, 2999.0, "wallet",        "cancelled_prepaid", None,       "Order cancelled before dispatch.",    "pending"),
        ("ORD-25005", "C001", "+91 98110 12345", 1799.0, 1799.0, "source_refund", "return_app",        "WELCOME",  "Wrong item delivered.",               "pending"),
        ("ORD-25006", "C002", "+91 97300 54321",  549.0,  499.0, "wallet",        "oos",               None,       "Item unavailable at store.",          "pending"),
        ("ORD-25007", "C003", "+91 99990 11223",  999.0,  799.0, "cod_wallet",    "manual",            None,       "Partial goodwill refund.",            "pending"),
        ("ORD-25008", "C004", "+91 98765 43210", 2499.0, 2499.0, "wallet",        "tnb",               None,       "T&B full refund.",                    "pending"),
        # processed (6)
        ("ORD-20234", "C007", "+91 98200 11111",  899.0,  699.0, "source_refund", "tnb",               None,       "T&B refund.",                         "processed"),
        ("ORD-20345", "C008", "+91 99887 66554", 2799.0, 2799.0, "wallet",        "oos",               None,       "Item OOS — full refund.",             "processed"),
        ("ORD-25009", "C005", "+91 98001 67890",  349.0,  299.0, "wallet",        "admin_panel",       None,       "Processing via Razorpay.",            "processed"),
        ("ORD-25010", "C006", "+91 97112 34567", 1599.0, 1199.0, "source_refund", "return_app",        "BABY20",   "Source refund initiated.",            "processed"),
        ("ORD-25011", "C007", "+91 98200 11111",  749.0,  749.0, "wallet",        "cancelled_prepaid", None,       "Cancelled — wallet credit queued.",   "processed"),
        ("ORD-25012", "C001", "+91 98110 12345", 4999.0, 4499.0, "source_refund", "manual",            None,       "High-value manual — under review.",   "processed"),
        # completed (10)
        ("ORD-20456", "C001", "+91 98110 12345", 1499.0,  924.0, "wallet",        "cancelled_prepaid", None,       "Order cancelled before dispatch.",    "completed"),
        ("ORD-20567", "C002", "+91 97300 54321",  229.0,  229.0, "cod_wallet",    "manual",            None,       "Manual goodwill refund.",             "completed"),
        ("ORD-25013", "C003", "+91 99990 11223",  599.0,  599.0, "wallet",        "return_app",        None,       "Return completed — wallet credited.", "completed"),
        ("ORD-25014", "C004", "+91 98765 43210", 1299.0,  999.0, "source_refund", "tnb",               None,       "T&B — source refund completed.",      "completed"),
        ("ORD-25015", "C005", "+91 98001 67890",  449.0,  449.0, "wallet",        "oos",               None,       "OOS refund completed.",               "completed"),
        ("ORD-25016", "C006", "+91 97112 34567",  899.0,  699.0, "cod_wallet",    "return_app",        "WELCOME",  "COD wallet completed.",               "completed"),
        ("ORD-25017", "C007", "+91 98200 11111",  349.0,  349.0, "wallet",        "manual",            None,       "Goodwill credit applied.",            "completed"),
        ("ORD-25018", "C008", "+91 99887 66554", 1999.0, 1799.0, "source_refund", "admin_panel",       "BACK15",   "Admin refund completed.",             "completed"),
        ("ORD-25019", "C001", "+91 98110 12345", 3499.0, 3499.0, "wallet",        "cancelled_prepaid", None,       "Bulk order cancelled — full refund.", "completed"),
        ("ORD-25020", "C002", "+91 97300 54321",  649.0,  549.0, "wallet",        "return_app",        None,       "Partial return — wallet credited.",   "completed"),
        # failed (4)
        ("ORD-20678", "C003", "+91 99990 11223",  399.0,  398.0, "wallet",        "return_app",        None,       "Rejected: duplicate request.",        "failed"),
        ("ORD-20789", "C004", "+91 98765 43210", 1099.0, 1099.0, "source_refund", "admin_panel",       None,       "Rejected: no valid reason.",          "failed"),
        ("ORD-25021", "C005", "+91 98001 67890",  799.0,  799.0, "wallet",        "manual",            None,       "Rejected: outside refund window.",    "failed"),
        ("ORD-25022", "C006", "+91 97112 34567",  499.0,  399.0, "cod_wallet",    "return_app",        None,       "Rejected: item not returned.",        "failed"),
    ]
    for (oid, cid, phone, ord_amt, amt, method, rtype, coupon, notes, status) in extra_refunds:
        completed_at = random_dt(3) if status == "completed" else None
        conn.execute(
            """INSERT INTO refunds
               (order_id, customer_id, customer_phone, order_amount, amount,
                method, refund_type, coupon_code, notes, status,
                triggered_at, completed_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (oid, cid, phone, ord_amt, amt, method, rtype, coupon, notes, status,
             random_dt(7), completed_at)
        )
        refunds_inserted += 1
    conn.commit()

    # ── CRM Calls ─────────────────────────────────────────────────────────────
    crm_order_num = 30000

    def next_order():
        nonlocal crm_order_num
        crm_order_num += 1
        return f"ORD-{crm_order_num}"

    # 15 × pending (unassigned)
    for i in range(15):
        cust = CRM_CUSTOMERS[i % len(CRM_CUSTOMERS)]
        conn.execute(
            """
            INSERT INTO crm_calls
                (order_id, customer_id, customer_phone, customer_name,
                 order_amount, order_status, new_repeat, coupon_code,
                 assigned_to, call_status, assigned_at)
            VALUES (?,?,?,?,?,?,?,?,NULL,'pending',?)
            """,
            (
                next_order(), cust[0], cust[2], cust[1],
                cust[3], random.choice(CRM_STATUSES),
                cust[4], random.choice(COUPON_CODES),
                random_dt(7),
            )
        )

    # 8 × in_progress (assigned to agents 1 or 2, partially filled)
    ip_reasons = DROP_OFF_REASONS[:4]
    for i in range(8):
        cust = CRM_CUSTOMERS[i % len(CRM_CUSTOMERS)]
        agent = (i % 2) + 1  # alternate between agent 1 and 2
        started = random_dt(3)
        conn.execute(
            """
            INSERT INTO crm_calls
                (order_id, customer_id, customer_phone, customer_name,
                 order_amount, order_status, new_repeat, coupon_code,
                 assigned_to, call_status, reached_out,
                 assigned_at, started_at)
            VALUES (?,?,?,?,?,?,?,?,?,'in_progress',?,?,?)
            """,
            (
                next_order(), cust[0], cust[2], cust[1],
                cust[3], random.choice(CRM_STATUSES),
                cust[4], random.choice(COUPON_CODES),
                agent, random.choice(["yes", "no", "attempted"]),
                random_dt(5), started,
            )
        )

    # 7 × completed (all fields filled)
    for i in range(7):
        cust = CRM_CUSTOMERS[i % len(CRM_CUSTOMERS)]
        agent = (i % 2) + 1
        started   = random_dt(10)
        completed = random_dt(7)
        conn.execute(
            """
            INSERT INTO crm_calls
                (order_id, customer_id, customer_phone, customer_name,
                 order_amount, order_status, new_repeat, coupon_code,
                 assigned_to, call_status,
                 reached_out, drop_off_reason, reordered, notes,
                 assigned_at, started_at, completed_at)
            VALUES (?,?,?,?,?,?,?,?,?,'completed',?,?,?,?,?,?,?)
            """,
            (
                next_order(), cust[0], cust[2], cust[1],
                cust[3], random.choice(CRM_STATUSES),
                cust[4], random.choice(COUPON_CODES),
                agent,
                random.choice(["yes", "no", "attempted"]),
                random.choice(DROP_OFF_REASONS),
                random.choice(["yes", "no"]),
                "Follow-up done successfully.",
                random_dt(12), started, completed,
            )
        )

    conn.commit()

    # ── Short-Pick Actions ────────────────────────────────────────────────────
    sp_order_num = 40000

    def next_sp_order():
        nonlocal sp_order_num
        sp_order_num += 1
        return f"ORD-{sp_order_num}"

    def random_items(n=None):
        n = n or random.randint(1, 3)
        picked = random.sample(SHORT_ITEMS_POOL, min(n, len(SHORT_ITEMS_POOL)))
        names = ", ".join(p[0] for p in picked)
        skus  = ", ".join(p[1] for p in picked)
        return names, skus, len(picked)

    # 10 × pending (unassigned)
    for i in range(10):
        cust = SHORT_PICK_CUSTOMERS[i % len(SHORT_PICK_CUSTOMERS)]
        items_str, skus_str, cnt = random_items()
        conn.execute(
            """
            INSERT INTO short_pick_actions
                (order_id, customer_id, customer_phone, customer_name,
                 order_amount, payment_method, store_code,
                 short_items, short_skus, short_item_count,
                 assigned_to, action_status, synced_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,NULL,'pending',?)
            """,
            (
                next_sp_order(), cust[0], cust[2], cust[1],
                cust[3], cust[4], cust[5],
                items_str, skus_str, cnt,
                random_dt(5),
            )
        )

    # 6 × in_progress (agents 1 or 2)
    for i in range(6):
        cust  = SHORT_PICK_CUSTOMERS[i % len(SHORT_PICK_CUSTOMERS)]
        agent = (i % 2) + 1
        items_str, skus_str, cnt = random_items()
        conn.execute(
            """
            INSERT INTO short_pick_actions
                (order_id, customer_id, customer_phone, customer_name,
                 order_amount, payment_method, store_code,
                 short_items, short_skus, short_item_count,
                 assigned_to, action_status, reached_out,
                 synced_at, started_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,'in_progress',?,?,?)
            """,
            (
                next_sp_order(), cust[0], cust[2], cust[1],
                cust[3], cust[4], cust[5],
                items_str, skus_str, cnt,
                agent, random.choice(["yes", "no", "attempted"]),
                random_dt(4), random_dt(2),
            )
        )

    # 6 × completed
    for i in range(6):
        cust  = SHORT_PICK_CUSTOMERS[i % len(SHORT_PICK_CUSTOMERS)]
        agent = (i % 2) + 1
        items_str, skus_str, cnt = random_items()
        conn.execute(
            """
            INSERT INTO short_pick_actions
                (order_id, customer_id, customer_phone, customer_name,
                 order_amount, payment_method, store_code,
                 short_items, short_skus, short_item_count,
                 assigned_to, action_status,
                 reached_out, customer_response, resolution, notes,
                 synced_at, started_at, completed_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,'completed',?,?,?,?,?,?,?)
            """,
            (
                next_sp_order(), cust[0], cust[2], cust[1],
                cust[3], cust[4], cust[5],
                items_str, skus_str, cnt,
                agent,
                random.choice(["yes", "attempted"]),
                random.choice(CUSTOMER_RESPONSES),
                random.choice(RESOLUTIONS),
                "Action completed after customer contact.",
                random_dt(10), random_dt(8), random_dt(5),
            )
        )

    conn.commit()
    conn.close()

    print(f"✓ Seeded {returns_inserted} returns, {refunds_inserted} refunds")
    print(f"✓ Seeded 30 CRM calls (15 pending / 8 in_progress / 7 completed)")
    print(f"✓ Seeded 22 short-pick actions (10 pending / 6 in_progress / 6 completed)")
    print(f"✓ Seeded {len(ROLE_PERMISSIONS)} role permissions across 5 roles")
    print("✓ Seed complete!")


if __name__ == "__main__":
    seed()
