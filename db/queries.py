"""
All DB read/write functions.  Uses ? placeholders throughout (SQLite).
MySQL migration: replace ? with %s and swap get_conn() to mysql.connector.
"""
from db.connection import get_conn


# ── Stores ────────────────────────────────────────────────────────────────────

def get_stores():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM stores ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── CX Users ──────────────────────────────────────────────────────────────────

def get_cx_users(active_only: bool = True):
    conn = get_conn()
    if active_only:
        rows = conn.execute(
            "SELECT * FROM cx_users WHERE is_active=1 ORDER BY name"
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM cx_users ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_cx_user_by_id(user_id: int) -> "dict | None":
    conn = get_conn()
    row = conn.execute("SELECT * FROM cx_users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_agents():
    """Return cx_users that can be assigned calls/tasks (not wh_user)."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM cx_users WHERE role IN ('agent','cx_lead','supervisor','admin') AND is_active=1 ORDER BY name"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def toggle_availability(user_id: int, available: bool) -> None:
    conn = get_conn()
    conn.execute(
        "UPDATE cx_users SET is_available=? WHERE id=?",
        (1 if available else 0, user_id)
    )
    conn.commit()
    conn.close()


# ── Call Assignment (round-robin) ─────────────────────────────────────────────

def assign_calls_to_available_agents() -> int:
    """
    Distribute all unassigned pending CRM calls equally among currently-available agents.
    Returns the number of calls assigned.
    """
    conn = get_conn()
    agents = conn.execute(
        "SELECT id FROM cx_users WHERE is_available=1 AND role IN ('agent','cx_lead','supervisor','admin') AND is_active=1"
    ).fetchall()
    calls = conn.execute(
        "SELECT id FROM crm_calls WHERE (assigned_to IS NULL OR assigned_to=0) AND call_status='pending'"
    ).fetchall()

    if not agents or not calls:
        conn.close()
        return 0

    agent_ids = [a["id"] for a in agents]
    assigned = 0
    for i, call in enumerate(calls):
        agent_id = agent_ids[i % len(agent_ids)]
        conn.execute(
            "UPDATE crm_calls SET assigned_to=?, assigned_at=CURRENT_TIMESTAMP WHERE id=?",
            (agent_id, call["id"])
        )
        assigned += 1
    conn.commit()
    conn.close()
    return assigned


# ── Returns ───────────────────────────────────────────────────────────────────

def get_returns(
    status_filter=None,
    store_id=None,
    agent_id=None,
    customer_search=None,
    date_from=None,
    date_to=None,
    type_filter=None,
    source_filter=None,
    payment_filter=None,
):
    conn = get_conn()
    conditions = []
    params = []
    if status_filter and status_filter != "all":
        conditions.append("r.status = ?")
        params.append(status_filter)
    if store_id:
        conditions.append("r.store_id = ?")
        params.append(store_id)
    if agent_id:
        conditions.append("r.agent_id = ?")
        params.append(agent_id)
    if customer_search:
        conditions.append("(r.customer_name LIKE ? OR r.customer_phone LIKE ?)")
        params.extend([f"%{customer_search}%", f"%{customer_search}%"])
    if date_from:
        conditions.append("date(r.created_at) >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("date(r.created_at) <= ?")
        params.append(date_to)
    if type_filter:
        conditions.append("r.type = ?")
        params.append(type_filter)
    if source_filter:
        conditions.append("r.source = ?")
        params.append(source_filter)
    if payment_filter:
        conditions.append("r.payment_method = ?")
        params.append(payment_filter)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    sql = f"""
        SELECT
            r.*,
            u.name  AS agent_name,
            s.name  AS store_name,
            COALESCE(SUM(ri.return_amount), 0)  AS total_return_value,
            COUNT(ri.id)                          AS item_count,
            GROUP_CONCAT(ri.item_name, ' | ')     AS item_names
        FROM returns r
        LEFT JOIN cx_users u      ON r.agent_id = u.id
        LEFT JOIN stores s        ON r.store_id = s.id
        LEFT JOIN return_items ri ON ri.return_id = r.id
        {where}
        GROUP BY r.id
        ORDER BY r.created_at DESC
    """
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_return_with_approval(
    order_id,
    customer_id,
    customer_phone,
    payment_method,
    ret_type,
    items,
    spoken,
    pitched,
    reason,
    refund_source,
    pickup_slot,
    notes,
    agent_id=None,
    source="cx_portal",
):
    """
    Create a return pre-filled with agent form fields, status=pending_approval.
    Used from Order Details page and manual create — skips pending_action entirely.
    """
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO returns
            (order_id, customer_id, customer_phone, payment_method, type, source, status,
             agent_id, spoken_to_customer, pitched_exchange, reason, refund_source, pickup_slot, agent_notes)
        VALUES (?, ?, ?, ?, ?, ?, 'pending_approval', ?, ?, ?, ?, ?, ?, ?)
        """,
        (order_id, customer_id or "", customer_phone, payment_method, ret_type, source,
         agent_id, spoken, pitched, reason, refund_source, pickup_slot, notes)
    )
    return_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    for item in items:
        conn.execute(
            """
            INSERT INTO return_items (return_id, item_name, item_sku, quantity, unit_price, return_amount)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (return_id, item["name"], item.get("sku") or None,
             item.get("qty", 1), item.get("unit_price", 0), item.get("return_amount", 0))
        )
    conn.commit()
    conn.close()
    return return_id


def get_returns_for_agent(agent_id: int, status: str = "pending_action"):
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT r.id, r.order_id, r.customer_name, r.status, r.type, r.created_at,
               COALESCE(SUM(ri.return_amount), 0) AS total_return_value
        FROM returns r
        LEFT JOIN return_items ri ON ri.return_id = r.id
        WHERE r.agent_id = ? AND r.status = ?
        GROUP BY r.id
        ORDER BY r.created_at DESC
        LIMIT 5
        """,
        (agent_id, status)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_return_by_id(return_id):
    conn = get_conn()
    row = conn.execute(
        """
        SELECT r.*, u.name AS agent_name, s.name AS store_name
        FROM returns r
        LEFT JOIN cx_users u ON r.agent_id = u.id
        LEFT JOIN stores s   ON r.store_id = s.id
        WHERE r.id = ?
        """,
        (return_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_return_items(return_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM return_items WHERE return_id=? ORDER BY id",
        (return_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_return_counts():
    conn = get_conn()
    rows = conn.execute("SELECT status, COUNT(*) AS cnt FROM returns GROUP BY status").fetchall()
    conn.close()
    return {r["status"]: r["cnt"] for r in rows}


def agent_submit_return(return_id, ret_type, spoken, pitched, reason, refund_source, pickup_slot, notes):
    conn = get_conn()
    conn.execute(
        """
        UPDATE returns SET
            type               = ?,
            spoken_to_customer = ?,
            pitched_exchange   = ?,
            reason             = ?,
            refund_source      = ?,
            pickup_slot        = ?,
            agent_notes        = ?,
            status             = 'pending_approval',
            updated_at         = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (ret_type, spoken, pitched, reason, refund_source, pickup_slot, notes, return_id)
    )
    conn.commit()
    conn.close()


def cx_lead_approve(return_id):
    conn = get_conn()
    conn.execute(
        "UPDATE returns SET status='pending_pickup', updated_at=CURRENT_TIMESTAMP WHERE id=?",
        (return_id,)
    )
    conn.commit()
    conn.close()


def cx_lead_reject(return_id, rejection_reason):
    conn = get_conn()
    conn.execute(
        "UPDATE returns SET status='cancelled', rejection_reason=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
        (rejection_reason, return_id)
    )
    conn.commit()
    conn.close()


def wh_send_to_pidge(return_id, store_id, pidge_tracking_id):
    conn = get_conn()
    conn.execute(
        """
        UPDATE returns SET
            store_id          = ?,
            pidge_tracking_id = ?,
            status            = 'out_for_pickup',
            updated_at        = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (store_id, pidge_tracking_id, return_id)
    )
    conn.commit()
    conn.close()


def simulate_pidge_complete(return_id):
    conn = get_conn()
    ret = conn.execute("SELECT * FROM returns WHERE id=?", (return_id,)).fetchone()
    if not ret:
        conn.close()
        return
    conn.execute(
        "UPDATE returns SET status='completed', updated_at=CURRENT_TIMESTAMP WHERE id=?",
        (return_id,)
    )
    if ret["type"] == "return":
        total = conn.execute(
            "SELECT COALESCE(SUM(return_amount), 0) AS tot FROM return_items WHERE return_id=?",
            (return_id,)
        ).fetchone()["tot"]
        method = ret["refund_source"] or "wallet"
        conn.execute(
            """INSERT INTO refunds
               (return_id, order_id, customer_id, amount, method, refund_type, status, completed_at)
               VALUES (?,?,?,?,?,'return_app','completed',CURRENT_TIMESTAMP)""",
            (return_id, ret["order_id"], ret["customer_id"], total, method)
        )
    conn.commit()
    conn.close()


# ── Refunds ───────────────────────────────────────────────────────────────────

def get_refunds(
    status_filter=None,
    customer_search=None,
    date_from=None,
    date_to=None,
    method_filter=None,
    refund_type_filter=None,
):
    conn = get_conn()
    conditions = []
    params = []
    if status_filter and status_filter != "all":
        if isinstance(status_filter, list):
            placeholders = ",".join("?" * len(status_filter))
            conditions.append(f"rf.status IN ({placeholders})")
            params.extend(status_filter)
        else:
            conditions.append("rf.status = ?")
            params.append(status_filter)
    if customer_search:
        conditions.append("(r.customer_name LIKE ? OR rf.customer_phone LIKE ?)")
        params.extend([f"%{customer_search}%", f"%{customer_search}%"])
    if date_from:
        conditions.append("date(rf.triggered_at) >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("date(rf.triggered_at) <= ?")
        params.append(date_to)
    if method_filter:
        conditions.append("rf.method = ?")
        params.append(method_filter)
    if refund_type_filter:
        conditions.append("rf.refund_type = ?")
        params.append(refund_type_filter)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    sql = f"""
        SELECT rf.*,
               r.customer_name,
               r.customer_phone AS return_phone,
               r.type           AS return_type,
               r.reason         AS return_reason,
               r.source         AS return_source
        FROM refunds rf
        LEFT JOIN returns r ON rf.return_id = r.id
        {where}
        ORDER BY rf.triggered_at DESC
    """
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_refund_by_id(refund_id: int):
    conn = get_conn()
    row = conn.execute(
        """
        SELECT rf.*,
               r.customer_name, r.customer_phone AS return_phone,
               r.type AS return_type, r.reason AS return_reason,
               r.source AS return_source, r.status AS return_status
        FROM refunds rf
        LEFT JOIN returns r ON rf.return_id = r.id
        WHERE rf.id = ?
        """,
        (refund_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_refund_counts():
    conn = get_conn()
    rows = conn.execute("SELECT status, COUNT(*) AS cnt FROM refunds GROUP BY status").fetchall()
    conn.close()
    return {r["status"]: r["cnt"] for r in rows}


def create_manual_refund(
    order_id,
    customer_id,
    customer_phone,
    order_amount,
    amount,
    method,
    refund_type,
    coupon_code,
    notes,
) -> int:
    """Create a manual refund at pending_approval status. Returns new refund_id."""
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO refunds
            (order_id, customer_id, customer_phone, order_amount, amount,
             method, refund_type, coupon_code, notes, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending_approval')
        """,
        (order_id, customer_id or "", customer_phone, order_amount, amount,
         method, refund_type, coupon_code, notes)
    )
    refund_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()
    return refund_id


def approve_refund(refund_id: int) -> None:
    conn = get_conn()
    conn.execute(
        "UPDATE refunds SET status='pending' WHERE id=? AND status='pending_approval'",
        (refund_id,)
    )
    conn.commit()
    conn.close()


def reject_refund(refund_id: int, reason: str = "") -> None:
    conn = get_conn()
    conn.execute(
        "UPDATE refunds SET status='failed', notes=COALESCE(notes||' | Rejected: '||?,'Rejected: '||?) WHERE id=?",
        (reason, reason, refund_id)
    )
    conn.commit()
    conn.close()


def process_refund(refund_id: int) -> None:
    conn = get_conn()
    conn.execute(
        "UPDATE refunds SET status='processed' WHERE id=? AND status='pending'",
        (refund_id,)
    )
    conn.commit()
    conn.close()


def complete_refund(refund_id: int) -> None:
    conn = get_conn()
    conn.execute(
        "UPDATE refunds SET status='completed', completed_at=CURRENT_TIMESTAMP WHERE id=? AND status='processed'",
        (refund_id,)
    )
    conn.commit()
    conn.close()


# ── CRM Calls ─────────────────────────────────────────────────────────────────

def get_crm_calls(
    call_status= None,
    assigned_to= None,
    order_status= None,
    date_from= None,
    date_to= None,
) -> list[dict]:
    conn = get_conn()
    conditions = []
    params = []
    if call_status and call_status != "all":
        conditions.append("c.call_status = ?")
        params.append(call_status)
    if assigned_to:
        conditions.append("c.assigned_to = ?")
        params.append(assigned_to)
    if order_status:
        conditions.append("c.order_status = ?")
        params.append(order_status)
    if date_from:
        conditions.append("date(c.assigned_at) >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("date(c.assigned_at) <= ?")
        params.append(date_to)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    sql = f"""
        SELECT c.*, u.name AS assigned_agent_name
        FROM crm_calls c
        LEFT JOIN cx_users u ON c.assigned_to = u.id
        {where}
        ORDER BY c.assigned_at DESC
    """
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_crm_call_by_id(call_id) -> "dict | None":
    conn = get_conn()
    row = conn.execute(
        """
        SELECT c.*, u.name AS assigned_agent_name
        FROM crm_calls c
        LEFT JOIN cx_users u ON c.assigned_to = u.id
        WHERE c.id = ?
        """,
        (call_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def start_crm_call(call_id) -> None:
    """Mark a call as in_progress when the agent opens it."""
    conn = get_conn()
    conn.execute(
        "UPDATE crm_calls SET call_status='in_progress', started_at=CURRENT_TIMESTAMP WHERE id=? AND call_status='pending'",
        (call_id,)
    )
    conn.commit()
    conn.close()


def save_crm_draft(call_id, reached_out, drop_off_reason, reordered, notes) -> None:
    """Save partial form data; keeps call in_progress."""
    conn = get_conn()
    conn.execute(
        """
        UPDATE crm_calls SET
            reached_out     = ?,
            drop_off_reason = ?,
            reordered       = ?,
            notes           = ?,
            call_status     = 'in_progress'
        WHERE id = ?
        """,
        (reached_out, drop_off_reason, reordered, notes, call_id)
    )
    conn.commit()
    conn.close()


def complete_crm_call(call_id, reached_out, drop_off_reason, reordered, notes) -> None:
    """Save all fields and mark call as completed."""
    conn = get_conn()
    conn.execute(
        """
        UPDATE crm_calls SET
            reached_out     = ?,
            drop_off_reason = ?,
            reordered       = ?,
            notes           = ?,
            call_status     = 'completed',
            completed_at    = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (reached_out, drop_off_reason, reordered, notes, call_id)
    )
    conn.commit()
    conn.close()


def get_crm_call_counts() -> dict:
    conn = get_conn()
    rows = conn.execute("SELECT call_status, COUNT(*) AS cnt FROM crm_calls GROUP BY call_status").fetchall()
    conn.close()
    return {r["call_status"]: r["cnt"] for r in rows}


def get_crm_calls_for_agent(agent_id: int, limit: int = 5) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT id, order_id, customer_name, call_status, order_status, assigned_at
        FROM crm_calls
        WHERE assigned_to=? AND call_status IN ('pending','in_progress')
        ORDER BY assigned_at DESC
        LIMIT ?
        """,
        (agent_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Short-Pick Actions ────────────────────────────────────────────────────────

def get_short_picks(
    action_status= None,
    assigned_to= None,
    store= None,
    date_from= None,
    date_to= None,
) -> list[dict]:
    conn = get_conn()
    conditions = []
    params = []
    if action_status and action_status != "all":
        conditions.append("sp.action_status = ?")
        params.append(action_status)
    if assigned_to:
        conditions.append("sp.assigned_to = ?")
        params.append(assigned_to)
    if store:
        conditions.append("sp.store_code = ?")
        params.append(store)
    if date_from:
        conditions.append("date(sp.synced_at) >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("date(sp.synced_at) <= ?")
        params.append(date_to)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    sql = f"""
        SELECT sp.*, u.name AS assigned_agent_name
        FROM short_pick_actions sp
        LEFT JOIN cx_users u ON sp.assigned_to = u.id
        {where}
        ORDER BY sp.synced_at DESC
    """
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_short_pick_by_id(sp_id) -> "dict | None":
    conn = get_conn()
    row = conn.execute(
        """
        SELECT sp.*, u.name AS assigned_agent_name
        FROM short_pick_actions sp
        LEFT JOIN cx_users u ON sp.assigned_to = u.id
        WHERE sp.id = ?
        """,
        (sp_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def start_short_pick(sp_id) -> None:
    conn = get_conn()
    conn.execute(
        "UPDATE short_pick_actions SET action_status='in_progress', started_at=CURRENT_TIMESTAMP WHERE id=? AND action_status='pending'",
        (sp_id,)
    )
    conn.commit()
    conn.close()


def save_short_pick_draft(sp_id, reached_out, customer_response, resolution, notes) -> None:
    conn = get_conn()
    conn.execute(
        """
        UPDATE short_pick_actions SET
            reached_out       = ?,
            customer_response = ?,
            resolution        = ?,
            notes             = ?,
            action_status     = 'in_progress'
        WHERE id = ?
        """,
        (reached_out, customer_response, resolution, notes, sp_id)
    )
    conn.commit()
    conn.close()


def complete_short_pick_action(sp_id, reached_out, customer_response, resolution, notes) -> None:
    conn = get_conn()
    conn.execute(
        """
        UPDATE short_pick_actions SET
            reached_out       = ?,
            customer_response = ?,
            resolution        = ?,
            notes             = ?,
            action_status     = 'completed',
            completed_at      = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (reached_out, customer_response, resolution, notes, sp_id)
    )
    conn.commit()
    conn.close()


def get_short_pick_counts() -> dict:
    conn = get_conn()
    rows = conn.execute(
        "SELECT action_status, COUNT(*) AS cnt FROM short_pick_actions GROUP BY action_status"
    ).fetchall()
    conn.close()
    return {r["action_status"]: r["cnt"] for r in rows}


def reassign_short_pick(sp_id: int, new_agent_id: int) -> None:
    conn = get_conn()
    conn.execute(
        "UPDATE short_pick_actions SET assigned_to=? WHERE id=?",
        (new_agent_id, sp_id)
    )
    conn.commit()
    conn.close()


def reassign_crm_call(call_id: int, new_agent_id: int) -> None:
    conn = get_conn()
    conn.execute(
        "UPDATE crm_calls SET assigned_to=? WHERE id=?",
        (new_agent_id, call_id)
    )
    conn.commit()
    conn.close()


def get_short_picks_for_agent(agent_id: int, limit: int = 5) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT id, order_id, customer_name, action_status, short_item_count, synced_at
        FROM short_pick_actions
        WHERE assigned_to=? AND action_status IN ('pending','in_progress')
        ORDER BY synced_at DESC
        LIMIT ?
        """,
        (agent_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Orders lookup ──────────────────────────────────────────────────────────────

def get_all_orders(search: str = "") -> list[dict]:
    """Return all orders (union of crm_calls, short_pick_actions, returns) matching search."""
    conn = get_conn()
    pattern = f"%{search}%" if search else "%"

    order_ids = set()
    for table in ("crm_calls", "short_pick_actions", "returns"):
        rows = conn.execute(
            f"SELECT DISTINCT order_id FROM {table} WHERE order_id LIKE ?", (pattern,)
        ).fetchall()
        order_ids.update(r["order_id"] for r in rows)

    result = []
    for oid in sorted(order_ids):
        crm = conn.execute(
            "SELECT customer_name, customer_phone, order_amount, order_status, call_status FROM crm_calls WHERE order_id=?",
            (oid,)
        ).fetchone()
        sp = conn.execute(
            "SELECT action_status FROM short_pick_actions WHERE order_id=?", (oid,)
        ).fetchone()
        ret = conn.execute(
            "SELECT status, type FROM returns WHERE order_id=? ORDER BY created_at DESC LIMIT 1", (oid,)
        ).fetchone()
        result.append({
            "order_id": oid,
            "customer_name": crm["customer_name"] if crm else None,
            "customer_phone": crm["customer_phone"] if crm else None,
            "order_amount": crm["order_amount"] if crm else None,
            "order_status": crm["order_status"] if crm else None,
            "crm_status": crm["call_status"] if crm else None,
            "short_pick_status": sp["action_status"] if sp else None,
            "return_status": ret["status"] if ret else None,
            "return_type": ret["type"] if ret else None,
        })
    conn.close()
    return result


# ── Customers lookup ───────────────────────────────────────────────────────────

def get_all_customers(search: str = "") -> list[dict]:
    """Return unique customers across all CX tables matching name or phone search."""
    conn = get_conn()
    pattern = f"%{search}%" if search else "%"

    phones: dict[str, str] = {}
    for table in ("crm_calls", "short_pick_actions", "returns"):
        rows = conn.execute(
            f"SELECT DISTINCT customer_phone, customer_name FROM {table} "
            f"WHERE customer_phone LIKE ? OR customer_name LIKE ?",
            (pattern, pattern)
        ).fetchall()
        for r in rows:
            phone = r["customer_phone"] or "unknown"
            if phone not in phones:
                phones[phone] = r["customer_name"]

    result = []
    for phone, name in phones.items():
        crm_count = conn.execute(
            "SELECT COUNT(*) FROM crm_calls WHERE customer_phone=?", (phone,)
        ).fetchone()[0]
        sp_count = conn.execute(
            "SELECT COUNT(*) FROM short_pick_actions WHERE customer_phone=?", (phone,)
        ).fetchone()[0]
        ret_count = conn.execute(
            "SELECT COUNT(*) FROM returns WHERE customer_phone=?", (phone,)
        ).fetchone()[0]
        result.append({
            "name": name or "—",
            "phone": phone,
            "crm_calls": crm_count,
            "short_picks": sp_count,
            "returns": ret_count,
        })

    conn.close()
    return sorted(result, key=lambda x: (x["name"] or "").lower())


# ── Returns — create from Orders module ───────────────────────────────────────

def check_return_exists(order_id: str) -> "dict | None":
    """Return the most recent returns record for this order_id, or None."""
    conn = get_conn()
    row = conn.execute(
        "SELECT id, status, type FROM returns WHERE order_id=? ORDER BY created_at DESC LIMIT 1",
        (order_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def create_return_from_order(
    order_id: str,
    customer_id: str,
    customer_phone: str,
    payment_method: str,
    ret_type: str,
    items: list,
) -> int:
    """
    Create a return record (status=pending_action, source=cx_portal) + line items.
    Returns the new return_id.
    items = [{"name": str, "sku": str, "qty": int, "unit_price": float, "return_amount": float}]
    """
    import uuid
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO returns
            (order_id, customer_id, customer_phone, payment_method, type, source, status)
        VALUES (?, ?, ?, ?, ?, 'cx_portal', 'pending_action')
        """,
        (order_id, customer_id or str(uuid.uuid4())[:8], customer_phone, payment_method, ret_type)
    )
    return_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    for item in items:
        conn.execute(
            """
            INSERT INTO return_items (return_id, item_name, item_sku, quantity, unit_price, return_amount)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (return_id, item["name"], item.get("sku") or None,
             item.get("qty", 1), item.get("unit_price", 0), item.get("return_amount", 0))
        )
    conn.commit()
    conn.close()
    return return_id


# ── Customer lookup (DB side) ──────────────────────────────────────────────────

def get_returns_for_customer(phone: str) -> list:
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT id, order_id, status, type, refund_source, created_at,
               COALESCE((SELECT SUM(ri.return_amount) FROM return_items ri WHERE ri.return_id=returns.id), 0) AS total_value
        FROM returns WHERE customer_phone=? ORDER BY created_at DESC
        """,
        (phone,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_crm_calls_for_customer(phone: str) -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT order_id, call_status, drop_off_reason, assigned_at FROM crm_calls WHERE customer_phone=? ORDER BY assigned_at DESC",
        (phone,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_wallet_credits_for_customer(customer_id: str, phone: str) -> float:
    """Sum of completed wallet/cod_wallet refunds for this customer."""
    conn = get_conn()
    # Try by customer_id first, then fall back to joining via returns.customer_phone
    row = conn.execute(
        """
        SELECT COALESCE(SUM(f.amount), 0) AS total
        FROM refunds f
        JOIN returns r ON r.id = f.return_id
        WHERE (f.customer_id = ? OR r.customer_phone = ?)
          AND f.method IN ('wallet', 'cod_wallet')
          AND f.status = 'completed'
        """,
        (customer_id or "", phone)
    ).fetchone()
    conn.close()
    return float(row["total"]) if row else 0.0


# ── Dashboard Stats ───────────────────────────────────────────────────────────

def get_dashboard_stats_admin() -> dict:
    """Aggregate metrics for admin/supervisor/cx_lead view."""
    conn = get_conn()

    open_returns = conn.execute(
        "SELECT COUNT(*) AS cnt FROM returns WHERE status NOT IN ('completed','cancelled')"
    ).fetchone()["cnt"]

    open_refunds = conn.execute(
        "SELECT COUNT(*) AS cnt FROM refunds WHERE status NOT IN ('completed','failed')"
    ).fetchone()["cnt"]

    open_calls = conn.execute(
        "SELECT COUNT(*) AS cnt FROM crm_calls WHERE call_status != 'completed'"
    ).fetchone()["cnt"]

    open_short_picks = conn.execute(
        "SELECT COUNT(*) AS cnt FROM short_pick_actions WHERE action_status != 'completed'"
    ).fetchone()["cnt"]

    conn.close()
    return {
        "open_returns":     open_returns,
        "open_refunds":     open_refunds,
        "open_calls":       open_calls,
        "open_short_picks": open_short_picks,
    }


def get_dashboard_stats_agent(user_id: int) -> dict:
    """Personal queue counts for an agent."""
    conn = get_conn()

    my_returns = conn.execute(
        "SELECT COUNT(*) AS cnt FROM returns WHERE agent_id=? AND status='pending_action'",
        (user_id,)
    ).fetchone()["cnt"]

    my_refunds = conn.execute(
        "SELECT COUNT(*) AS cnt FROM refunds rf JOIN returns r ON rf.return_id=r.id WHERE r.agent_id=? AND rf.status='pending'",
        (user_id,)
    ).fetchone()["cnt"]

    my_calls = conn.execute(
        "SELECT COUNT(*) AS cnt FROM crm_calls WHERE assigned_to=? AND call_status IN ('pending','in_progress')",
        (user_id,)
    ).fetchone()["cnt"]

    my_short_picks = conn.execute(
        "SELECT COUNT(*) AS cnt FROM short_pick_actions WHERE assigned_to=? AND action_status IN ('pending','in_progress')",
        (user_id,)
    ).fetchone()["cnt"]

    conn.close()
    return {
        "my_returns":     my_returns,
        "my_refunds":     my_refunds,
        "my_calls":       my_calls,
        "my_short_picks": my_short_picks,
    }


def get_agent_queue_summary() -> list[dict]:
    """Team-level queue breakdown for admin/supervisor view."""
    conn = get_conn()
    agents = conn.execute(
        "SELECT id, name, role, is_available FROM cx_users WHERE is_active=1 AND role != 'wh_user' ORDER BY name"
    ).fetchall()
    result = []
    for a in agents:
        aid = a["id"]
        ret_cnt = conn.execute(
            "SELECT COUNT(*) AS c FROM returns WHERE agent_id=? AND status='pending_action'", (aid,)
        ).fetchone()["c"]
        call_cnt = conn.execute(
            "SELECT COUNT(*) AS c FROM crm_calls WHERE assigned_to=? AND call_status IN ('pending','in_progress')", (aid,)
        ).fetchone()["c"]
        sp_cnt = conn.execute(
            "SELECT COUNT(*) AS c FROM short_pick_actions WHERE assigned_to=? AND action_status IN ('pending','in_progress')", (aid,)
        ).fetchone()["c"]
        result.append({
            "id":           aid,
            "name":         a["name"],
            "role":         a["role"],
            "is_available": bool(a["is_available"]),
            "returns":      ret_cnt,
            "calls":        call_cnt,
            "short_picks":  sp_cnt,
        })
    conn.close()
    return result
