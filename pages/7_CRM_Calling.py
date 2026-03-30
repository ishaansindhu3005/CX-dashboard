import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, date
from db.queries import (
    get_crm_calls, get_crm_call_by_id, get_crm_call_counts,
    start_crm_call, save_crm_draft, complete_crm_call,
    get_cx_users, reassign_crm_call,
)
from db.connection import init_db
from utils.rbac import has_permission

init_db()

from utils.page_utils import get_page_user
role, user = get_page_user()

# ── Constants ─────────────────────────────────────────────────────────────────

CALL_STATUS_COLOURS = {
    "pending":     "#f0a500",
    "in_progress": "#1a73e8",
    "completed":   "#2e7d32",
}

ORDER_STATUS_COLOURS = {
    "rto_out_for_delivery": "#7b1fa2",
    "rto_delivered":        "#6d28d9",
    "cancelled":            "#c62828",
    "canceled":             "#c62828",
    "failed":               "#991b1b",
    "undelivered":          "#ea580c",
    "pending":              "#f0a500",
}

DROP_OFF_REASONS = [
    ("cx_unavailable",      "CX Unavailable"),
    ("not_interested",      "Not Interested"),
    ("price_too_expensive", "Price Too Expensive"),
    ("bad_delivery",        "Didn't Like Delivery"),
    ("forgot_coupon",       "Forgot Coupon"),
    ("too_slow",            "Delivery Too Slow"),
    ("product_quality",     "Product Quality Issue"),
    ("other",               "Other"),
]

DEFAULT_FLEXI = ["New/Repeat", "Coupon Code", "Assigned Agent"]


def fmt_dt(s):
    if not s:
        return "—"
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S").strftime("%d %b %Y, %I:%M %p")
    except Exception:
        return str(s)


def call_badge(status):
    colour = CALL_STATUS_COLOURS.get(status, "#444")
    label  = status.replace("_", " ").title()
    return (
        f'<span style="background:{colour};color:#fff;padding:2px 9px;'
        f'border-radius:12px;font-size:0.78rem;font-weight:600">{label}</span>'
    )


def order_status_badge(status):
    colour = ORDER_STATUS_COLOURS.get(status, "#64748b")
    label  = status.replace("_", " ").title()
    return (
        f'<span style="background:{colour};color:#fff;padding:2px 8px;'
        f'border-radius:10px;font-size:0.75rem;font-weight:500">{label}</span>'
    )


# ── Detail panel ──────────────────────────────────────────────────────────────

def _render_detail_panel(call_id, role, tab_key, agents):
    call = get_crm_call_by_id(call_id)
    if not call:
        st.error("Call record not found.")
        return

    # Auto-mark in_progress when opened
    if call["call_status"] == "pending":
        start_crm_call(call_id)
        call["call_status"] = "in_progress"

    st.markdown("---")
    left, right = st.columns([1.2, 0.8])

    # ── Right: order context (read-only) ──────────────────────────────────────
    with right:
        st.markdown("#### 📋 Call Context")
        st.markdown(f"**Order ID:** `{call['order_id']}`")
        st.markdown(f"**Customer:** {call['customer_name'] or '—'}")
        st.markdown(f"**Phone:** {call['customer_phone'] or '—'}")
        st.markdown(f"**Amount:** ₹{call['order_amount']:,.0f}" if call.get("order_amount") else "**Amount:** —")
        st.markdown(
            f"**Order Status:** {order_status_badge(call['order_status'] or 'unknown')}",
            unsafe_allow_html=True,
        )
        nr = call.get("new_repeat")
        if nr:
            st.markdown(f"**Customer Type:** {'🆕 New' if nr == 'new' else '🔄 Repeat'}")
        cp = call.get("coupon_code")
        if cp:
            st.markdown(f"**Coupon:** `{cp}`")
        st.markdown(f"**Assigned To:** {call.get('assigned_agent_name') or '—'}")
        st.markdown(f"**Assigned At:** {fmt_dt(call.get('assigned_at'))}")
        if call.get("started_at"):
            st.markdown(f"**Started At:** {fmt_dt(call['started_at'])}")
        if call.get("completed_at"):
            st.markdown(f"**Completed At:** {fmt_dt(call['completed_at'])}")

        # Admin/Supervisor: reassign
        if has_permission(role, "crm_calling", "reassign") and call["call_status"] != "completed":
            st.markdown("---")
            st.markdown("**Reassign**")
            agent_opts = {a["id"]: a["name"] for a in agents}
            new_agent = st.selectbox(
                "Assign to",
                list(agent_opts.keys()),
                format_func=lambda x: agent_opts[x],
                index=list(agent_opts.keys()).index(call["assigned_to"]) if call.get("assigned_to") in agent_opts else 0,
                key=f"reassign_{call_id}_{tab_key}",
            )
            if st.button("Save Assignment", key=f"do_reassign_{call_id}_{tab_key}"):
                reassign_crm_call(call_id, new_agent)
                st.success("Reassigned.")
                st.rerun()

    # ── Left: form ────────────────────────────────────────────────────────────
    with left:
        c_close, c_title = st.columns([1, 6])
        with c_close:
            if st.button("✕", key=f"close_{call_id}_{tab_key}", help="Close panel"):
                st.session_state[f"selected_{tab_key}"] = None
                st.rerun()
        with c_title:
            st.markdown(f"#### CAL-{call_id:03d}")

        st.markdown(call_badge(call["call_status"]), unsafe_allow_html=True)
        st.markdown("")

        can_act = has_permission(role, "crm_calling", "call")

        if call["call_status"] == "completed" or not can_act:
            # ── Read-only ─────────────────────────────────────────────────────
            st.markdown("**Call outcome**")
            st.markdown(f"- Reached out: **{(call.get('reached_out') or '—').title()}**")
            reason_map = dict(DROP_OFF_REASONS)
            st.markdown(f"- Drop-off reason: **{reason_map.get(call.get('drop_off_reason') or '', call.get('drop_off_reason') or '—')}**")
            st.markdown(f"- Reordered: **{(call.get('reordered') or '—').title()}**")
            if call.get("notes"):
                st.markdown(f"- Notes: *{call['notes']}*")
            if call["call_status"] == "completed":
                st.success("Call completed.")
            elif not can_act:
                st.info("You have view-only access to this module.")

        else:
            # ── Editable form ─────────────────────────────────────────────────
            # Pre-fill with saved draft values (if any)
            pre_reached = call.get("reached_out") or "yes"
            pre_reason  = call.get("drop_off_reason") or DROP_OFF_REASONS[0][0]
            pre_reorder = call.get("reordered") or "no"
            pre_notes   = call.get("notes") or ""

            reached_options = ["yes", "no", "attempted"]
            reached_labels  = {"yes": "Yes", "no": "No", "attempted": "Attempted"}
            r_idx = reached_options.index(pre_reached) if pre_reached in reached_options else 0

            reorder_options = ["yes", "no"]
            reorder_labels  = {"yes": "Yes", "no": "No"}
            re_idx = reorder_options.index(pre_reorder) if pre_reorder in reorder_options else 1

            reason_options = [k for k, _ in DROP_OFF_REASONS]
            reason_labels_map = dict(DROP_OFF_REASONS)
            rs_idx = reason_options.index(pre_reason) if pre_reason in reason_options else 0

            reached_out = st.radio(
                "Did you reach out to the customer?",
                reached_options,
                format_func=lambda x: reached_labels[x],
                index=r_idx,
                horizontal=True,
                key=f"reached_{call_id}_{tab_key}",
            )
            drop_off = st.selectbox(
                "Why did the customer drop off?",
                reason_options,
                format_func=lambda x: reason_labels_map[x],
                index=rs_idx,
                key=f"reason_{call_id}_{tab_key}",
            )
            reordered = st.radio(
                "Did the customer place an order again?",
                reorder_options,
                format_func=lambda x: reorder_labels[x],
                index=re_idx,
                horizontal=True,
                key=f"reorder_{call_id}_{tab_key}",
            )
            notes = st.text_area(
                "Notes (optional)",
                value=pre_notes,
                height=80,
                key=f"notes_{call_id}_{tab_key}",
            )

            col_draft, col_submit = st.columns(2)
            with col_draft:
                if st.button("💾 Save Draft", key=f"draft_{call_id}_{tab_key}", use_container_width=True):
                    save_crm_draft(call_id, reached_out, drop_off, reordered, notes)
                    st.info("Draft saved.")
                    st.rerun()
            with col_submit:
                if st.button("✓ Submit", key=f"submit_{call_id}_{tab_key}", type="primary", use_container_width=True):
                    # All 3 required fields must be set
                    if not reached_out or not drop_off or not reordered:
                        st.error("Please fill all required fields before submitting.")
                    else:
                        complete_crm_call(call_id, reached_out, drop_off, reordered, notes)
                        st.success("Call completed!")
                        st.session_state[f"selected_{tab_key}"] = None
                        st.rerun()

    st.markdown("---")


# ── Tab renderer ──────────────────────────────────────────────────────────────

def _render_tab(tab_status, role, user, agents, flexi_cols, show_filters=False):
    # ── Filters (Pending tab only) ────────────────────────────────────────────
    order_status_filter = None
    date_from = date_to = None

    if show_filters:
        with st.expander("🔍 Filters", expanded=False):
            f1, f2, f3 = st.columns(3)
            order_status_filter = f1.selectbox(
                "Order Status",
                ["All", "cancelled", "failed", "undelivered", "pending",
                 "rto_out_for_delivery", "rto_delivered"],
                key=f"os_filter_{tab_status}",
            )
            if order_status_filter == "All":
                order_status_filter = None
            date_range = f2.date_input(
                "Date range",
                value=(date.today().replace(day=1), date.today()),
                key=f"date_filter_{tab_status}",
            )
            if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
                date_from = str(date_range[0])
                date_to   = str(date_range[1])

    # Agent-level: filter to own calls by default
    assigned_filter = None
    if role == "agent":
        assigned_filter = user.get("id")

    calls = get_crm_calls(
        call_status=None if tab_status == "all" else tab_status,
        assigned_to=assigned_filter,
        order_status=order_status_filter,
        date_from=date_from,
        date_to=date_to,
    )

    total_val = sum(c.get("order_amount") or 0 for c in calls)
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Calls", len(calls))
    m2.metric("Order Value", f"₹{total_val:,.0f}")
    m3.metric("Completed",   sum(1 for c in calls if c["call_status"] == "completed"))

    st.divider()

    if not calls:
        st.info("No calls in this category.")
        return

    # ── Column header ─────────────────────────────────────────────────────────
    show_new_repeat  = "New/Repeat"    in flexi_cols
    show_coupon      = "Coupon Code"   in flexi_cols
    show_assigned    = "Assigned Agent" in flexi_cols

    # Build dynamic column widths
    col_widths = [0.7, 1.1, 1.4, 1.0, 1.1, 1.1]  # ID, Order, Customer, Amount, Order Status, Call Status
    col_headers = ["ID", "Order", "Customer", "Amount", "Order Status", "Call Status"]
    if show_new_repeat:
        col_widths.append(0.9)
        col_headers.append("Type")
    if show_coupon:
        col_widths.append(0.9)
        col_headers.append("Coupon")
    if show_assigned:
        col_widths.append(1.3)
        col_headers.append("Assigned To")
    col_widths.append(0.6)
    col_headers.append("")

    h = st.columns(col_widths)
    for col, label in zip(h, col_headers):
        col.markdown(f"**{label}**")
    st.markdown('<hr style="margin:2px 0 8px 0">', unsafe_allow_html=True)

    selected_key = f"selected_{tab_status}"
    if selected_key not in st.session_state:
        st.session_state[selected_key] = None

    for c in calls:
        row = st.columns(col_widths)
        idx = 0
        row[idx].write(f"CAL-{c['id']:03d}");  idx += 1
        row[idx].write(c["order_id"]);          idx += 1
        row[idx].write(c["customer_name"] or "—"); idx += 1
        row[idx].write(f"₹{c['order_amount']:,.0f}" if c.get("order_amount") else "—"); idx += 1
        row[idx].markdown(order_status_badge(c.get("order_status") or ""), unsafe_allow_html=True); idx += 1
        row[idx].markdown(call_badge(c["call_status"]), unsafe_allow_html=True); idx += 1
        if show_new_repeat:
            nr = c.get("new_repeat") or "—"
            row[idx].write("🆕 New" if nr == "new" else ("🔄 Repeat" if nr == "repeat" else nr)); idx += 1
        if show_coupon:
            row[idx].write(c.get("coupon_code") or "—"); idx += 1
        if show_assigned:
            row[idx].write(c.get("assigned_agent_name") or "—"); idx += 1

        btn_label = "Close" if st.session_state[selected_key] == c["id"] else "Open"
        if row[idx].button(btn_label, key=f"btn_{c['id']}_{tab_status}"):
            st.session_state[selected_key] = None if st.session_state[selected_key] == c["id"] else c["id"]
            st.rerun()

        if st.session_state[selected_key] == c["id"]:
            _render_detail_panel(c["id"], role, tab_status, agents)


# ── Page ──────────────────────────────────────────────────────────────────────

st.markdown("## 📞 CRM Calling")

agents = get_cx_users(active_only=True)
counts = get_crm_call_counts()

# ── Column picker ─────────────────────────────────────────────────────────────
with st.expander("⚙️ Columns", expanded=False):
    flexi_cols = st.multiselect(
        "Optional columns",
        ["New/Repeat", "Coupon Code", "Assigned Agent"],
        default=["New/Repeat", "Coupon Code", "Assigned Agent"],
        key="crm_flexi",
    )

total = sum(counts.values())

if role == "agent":
    tab_defs = [
        ("all",         "All"),
        ("pending",     "Pending"),
        ("in_progress", "In Progress"),
        ("completed",   "Completed"),
    ]
else:
    tab_defs = [
        ("all",         f"All  ({total})"),
        ("pending",     f"Pending  ({counts.get('pending', 0)})"),
        ("in_progress", f"In Progress  ({counts.get('in_progress', 0)})"),
        ("completed",   f"Completed  ({counts.get('completed', 0)})"),
    ]

tabs = st.tabs([label for _, label in tab_defs])

for tab_obj, (status_key, _) in zip(tabs, tab_defs):
    with tab_obj:
        _render_tab(
            tab_status=status_key,
            role=role,
            user=user,
            agents=agents,
            flexi_cols=flexi_cols,
            show_filters=(status_key == "pending"),
        )
