import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, date
from db.queries import (
    get_refunds, get_refund_counts, get_refund_by_id,
    create_manual_refund, approve_refund, reject_refund,
    process_refund, complete_refund,
)
from db.connection import init_db

init_db()

from utils.page_utils import get_page_user
from utils.rbac import has_permission

role, user = get_page_user()

# ── Constants ─────────────────────────────────────────────────────────────────

STATUS_COLOURS = {
    "pending_approval": "#7c3aed",
    "pending":          "#f0a500",
    "processed":        "#0284c7",
    "completed":        "#2e7d32",
    "failed":           "#c62828",
}

METHOD_LABELS = {
    "wallet":        "💳 Wallet",
    "source_refund": "🏦 Source Refund",
    "cod_wallet":    "💼 COD Wallet",
}

REFUND_TYPE_LABELS = {
    "return_app":         "Return App",
    "admin_panel":        "Admin Panel",
    "chatbot":            "Chatbot",
    "tnb":                "T&B",
    "oos":                "OOS",
    "cancelled_prepaid":  "Cancelled (Prepaid)",
    "manual":             "Manual",
}

RETURN_STATUS_COLOURS = {
    "pending_action":   "#6b7280",
    "pending_approval": "#7c3aed",
    "pending_pickup":   "#f0a500",
    "out_for_pickup":   "#0284c7",
    "completed":        "#2e7d32",
    "cancelled":        "#c62828",
}


def fmt_dt(s):
    if not s:
        return "—"
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S").strftime("%d %b %Y, %I:%M %p")
    except Exception:
        return str(s)


def status_badge(status, colour_map=None):
    if colour_map is None:
        colour_map = STATUS_COLOURS
    colour = colour_map.get(status, "#444")
    label = status.replace("_", " ").title()
    return (
        f'<span style="background:{colour};color:#fff;padding:2px 9px;'
        f'border-radius:12px;font-size:0.78rem;font-weight:600">'
        f'{label}</span>'
    )


def method_pill(method):
    return METHOD_LABELS.get(method, method.replace("_", " ").title() if method else "—")


# ── Manual refund form ────────────────────────────────────────────────────────

def _render_manual_create():
    st.markdown("### ＋ Manual Refund")
    with st.form("manual_refund_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        order_id      = c1.text_input("Order ID *")
        customer_id   = c2.text_input("Customer ID")
        customer_phone = c1.text_input("Customer Phone *")
        order_amount  = c2.number_input("Order Amount (₹)", min_value=0.0, step=1.0)
        amount        = c1.number_input("Refund Amount (₹) *", min_value=0.01, step=1.0)
        method        = c2.selectbox("Refund Method *", ["wallet", "source_refund", "cod_wallet"],
                                     format_func=lambda x: METHOD_LABELS.get(x, x))
        refund_type   = c1.selectbox("Refund Type *",
                                     list(REFUND_TYPE_LABELS.keys()),
                                     format_func=lambda x: REFUND_TYPE_LABELS.get(x, x))
        coupon_code   = c2.text_input("Coupon Code (if applicable)")
        notes         = st.text_area("Notes")

        submitted = st.form_submit_button("Submit for Approval", type="primary", use_container_width=True)
        if submitted:
            errors = []
            if not order_id.strip():
                errors.append("Order ID is required.")
            if not customer_phone.strip():
                errors.append("Customer Phone is required.")
            if amount <= 0:
                errors.append("Refund Amount must be > 0.")
            if errors:
                for e in errors:
                    st.error(e)
            else:
                rid = create_manual_refund(
                    order_id=order_id.strip(),
                    customer_id=customer_id.strip() or order_id.strip(),
                    customer_phone=customer_phone.strip(),
                    order_amount=order_amount,
                    amount=amount,
                    method=method,
                    refund_type=refund_type,
                    coupon_code=coupon_code.strip() or None,
                    notes=notes.strip() or None,
                )
                st.success(f"Refund REF-{rid:03d} submitted for approval.")
                st.session_state["show_manual_refund"] = False
                st.rerun()


# ── Detail panel ──────────────────────────────────────────────────────────────

def _render_detail(refund_id: int):
    r = get_refund_by_id(refund_id)
    if not r:
        st.error("Refund not found.")
        return

    can_approve = has_permission(role, "refunds", "approve")

    st.markdown(f"#### REF-{r['id']:03d} — {r['order_id']}")
    c1, c2 = st.columns(2)

    # Left: refund info
    with c1:
        st.markdown("**Refund Details**")
        st.markdown(f"Customer: `{r['customer_phone'] or r['customer_id']}`")
        st.markdown(f"Amount: **₹{r['amount']:,.0f}**")
        if r.get("order_amount"):
            st.markdown(f"Order Amount: ₹{r['order_amount']:,.0f}")
        st.markdown(f"Method: {method_pill(r['method'])}")
        rtype = r.get("refund_type")
        if rtype:
            st.markdown(f"Type: {REFUND_TYPE_LABELS.get(rtype, rtype)}")
        if r.get("coupon_code"):
            st.markdown(f"Coupon: `{r['coupon_code']}`")
        if r.get("notes"):
            st.markdown(f"Notes: {r['notes']}")
        st.markdown(f"Triggered: {fmt_dt(r['triggered_at'])}")
        if r.get("completed_at"):
            st.markdown(f"Completed: {fmt_dt(r['completed_at'])}")

    # Right: return link or status
    with c2:
        if r.get("return_id"):
            st.markdown("**Linked Return**")
            ret_status = r.get("return_status") or "—"
            st.markdown(
                f"Return ID: **RET-{r['return_id']:03d}**<br>"
                f"Status: {status_badge(ret_status, RETURN_STATUS_COLOURS)}<br>"
                f"Type: {(r.get('return_type') or '—').title()}<br>"
                f"Reason: {r.get('return_reason') or '—'}",
                unsafe_allow_html=True,
            )
        else:
            st.markdown("**No linked return** (standalone refund)")

        st.markdown("---")
        st.markdown(
            f"**Current Status:** {status_badge(r['status'])}",
            unsafe_allow_html=True,
        )

        # Action buttons based on status + role
        status = r["status"]
        if status == "pending_approval" and can_approve:
            ba, br = st.columns(2)
            if ba.button("✅ Approve", key=f"appr_{refund_id}", type="primary"):
                approve_refund(refund_id)
                st.success("Refund approved → Pending.")
                st.rerun()
            rejection_reason = st.text_input("Rejection reason (required to reject)", key=f"rr_{refund_id}")
            if br.button("❌ Reject", key=f"rej_{refund_id}"):
                if not rejection_reason.strip():
                    st.error("Please enter a rejection reason.")
                else:
                    reject_refund(refund_id, rejection_reason.strip())
                    st.error("Refund rejected → Failed.")
                    st.rerun()

        elif status == "pending" and can_approve:
            if st.button("🔄 Mark Processed", key=f"proc_{refund_id}", type="primary"):
                process_refund(refund_id)
                st.info("Refund marked as Processed.")
                st.rerun()

        elif status == "processed" and can_approve:
            if st.button("✔ Mark Completed", key=f"comp_{refund_id}", type="primary"):
                complete_refund(refund_id)
                st.success("Refund completed.")
                st.rerun()


# ── Tab renderer ──────────────────────────────────────────────────────────────

def _render_tab(status_key):
    # Filters expander
    with st.expander("Filters", expanded=False):
        fc1, fc2, fc3, fc4 = st.columns(4)
        customer_search  = fc1.text_input("Customer (name/phone)", key=f"cs_{status_key}")
        method_f         = fc2.selectbox(
            "Method", ["All", "wallet", "source_refund", "cod_wallet"],
            format_func=lambda x: METHOD_LABELS.get(x, x) if x != "All" else "All",
            key=f"mf_{status_key}"
        )
        refund_type_f = fc3.selectbox(
            "Type", ["All"] + list(REFUND_TYPE_LABELS.keys()),
            format_func=lambda x: REFUND_TYPE_LABELS.get(x, x) if x != "All" else "All",
            key=f"rtf_{status_key}"
        )
        fd1, fd2 = fc4.columns(2)
        date_from = fd1.date_input("From", value=None, key=f"df_{status_key}")
        date_to   = fd2.date_input("To",   value=None, key=f"dt_{status_key}")

    refunds = get_refunds(
        status_filter    = None if status_key == "all" else status_key,
        customer_search  = customer_search.strip() or None,
        date_from        = str(date_from) if date_from else None,
        date_to          = str(date_to)   if date_to   else None,
        method_filter    = method_f         if method_f != "All" else None,
        refund_type_filter = refund_type_f  if refund_type_f != "All" else None,
    )

    total_amount = sum(r["amount"] for r in refunds)
    m1, m2 = st.columns(2)
    m1.metric("Refunds", len(refunds))
    m2.metric("Total Amount", f"₹{total_amount:,.0f}")

    st.divider()

    if not refunds:
        st.info("No refunds found.")
        return

    # Header row
    COL_W = [0.6, 1.1, 1.3, 0.9, 1.0, 1.0, 1.1, 0.9, 1.3, 0.6]
    HDRS  = ["ID", "Order", "Customer", "Ord Amt", "Refund", "Method", "Type", "Return?", "Status", ""]
    h = st.columns(COL_W)
    for col, lbl in zip(h, HDRS):
        col.markdown(f"**{lbl}**")
    st.markdown('<hr style="margin:2px 0 8px 0">', unsafe_allow_html=True)

    open_key = f"open_refund_{status_key}"
    if open_key not in st.session_state:
        st.session_state[open_key] = None

    for r in refunds:
        row = st.columns(COL_W)
        row[0].write(f"REF-{r['id']:03d}")
        row[1].write(r["order_id"])
        row[2].write(r.get("customer_phone") or r["customer_id"])
        ord_amt = r.get("order_amount")
        row[3].write(f"₹{ord_amt:,.0f}" if ord_amt else "—")
        row[4].write(f"₹{r['amount']:,.0f}")
        row[5].write(method_pill(r["method"]))
        rtype = r.get("refund_type") or ""
        row[6].write(REFUND_TYPE_LABELS.get(rtype, rtype.replace("_", " ").title() if rtype else "—"))
        row[7].write(f"RET-{r['return_id']:03d}" if r.get("return_id") else "—")
        row[8].markdown(status_badge(r["status"]), unsafe_allow_html=True)
        btn_label = "Close" if st.session_state[open_key] == r["id"] else "Open"
        if row[9].button(btn_label, key=f"open_{status_key}_{r['id']}"):
            st.session_state[open_key] = None if st.session_state[open_key] == r["id"] else r["id"]
            st.rerun()

        if st.session_state[open_key] == r["id"]:
            with st.container():
                st.markdown(
                    '<div style="background:#f8fafc;border:1px solid #e2e8f0;'
                    'border-radius:8px;padding:16px;margin:8px 0">',
                    unsafe_allow_html=True,
                )
                _render_detail(r["id"])
                st.markdown("</div>", unsafe_allow_html=True)


# ── Page ──────────────────────────────────────────────────────────────────────

st.markdown("## 💰 Refunds")

# Top-right manual refund button
can_create = has_permission(role, "refunds", "create")
if can_create:
    hdr_l, hdr_r = st.columns([4, 1])
    with hdr_r:
        if st.button("＋ Manual Refund", use_container_width=True, type="secondary"):
            st.session_state["show_manual_refund"] = not st.session_state.get("show_manual_refund", False)

if st.session_state.get("show_manual_refund", False):
    with st.container():
        st.markdown(
            '<div style="background:#f1f5f9;border:1px solid #cbd5e1;border-radius:8px;padding:16px;margin-bottom:12px">',
            unsafe_allow_html=True,
        )
        _render_manual_create()
        st.markdown("</div>", unsafe_allow_html=True)

# Tabs
counts = get_refund_counts()
total  = sum(counts.values())

tab_defs = [
    ("all",              f"All  ({total})"),
    ("pending_approval", f"Pending Approval  ({counts.get('pending_approval', 0)})"),
    ("pending",          f"Pending  ({counts.get('pending', 0)})"),
    ("processed",        f"Processed  ({counts.get('processed', 0)})"),
    ("completed",        f"Completed  ({counts.get('completed', 0)})"),
    ("failed",           f"Failed  ({counts.get('failed', 0)})"),
]

tabs = st.tabs([label for _, label in tab_defs])
for tab_obj, (status_key, _) in zip(tabs, tab_defs):
    with tab_obj:
        _render_tab(status_key)
