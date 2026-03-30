import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, date
from db.queries import (
    get_short_picks, get_short_pick_by_id, get_short_pick_counts,
    start_short_pick, save_short_pick_draft, complete_short_pick_action,
    get_cx_users, reassign_short_pick,
)
from db.connection import init_db
from utils.rbac import has_permission
from utils.oms_sync import sync_short_picks_from_oms

init_db()

from utils.page_utils import get_page_user
role, user = get_page_user()

# ── Constants ─────────────────────────────────────────────────────────────────

STATUS_COLOURS = {
    "pending":     "#f0a500",
    "in_progress": "#1a73e8",
    "completed":   "#2e7d32",
}

CUSTOMER_RESPONSES = [
    "Understood & Accepted",
    "Upset",
    "Wants Full Refund",
    "Wants Replacement",
    "No Response",
    "Other",
]

RESOLUTIONS = [
    "Refund Initiated",
    "Replacement Arranged",
    "Partial Refund",
    "Customer Cancelled",
    "No Action Needed",
    "Other",
]


def fmt_dt(s):
    if not s:
        return "—"
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S").strftime("%d %b %Y, %I:%M %p")
    except Exception:
        return str(s)


def status_badge(status):
    colour = STATUS_COLOURS.get(status, "#444")
    label  = status.replace("_", " ").title()
    return (
        f'<span style="background:{colour};color:#fff;padding:2px 9px;'
        f'border-radius:12px;font-size:0.78rem;font-weight:600">{label}</span>'
    )


def item_count_badge(n):
    return (
        f'<span style="background:#e0f2fe;color:#0369a1;padding:1px 7px;'
        f'border-radius:10px;font-size:0.78rem;font-weight:600">{n} item{"s" if n != 1 else ""}</span>'
    )


# ── Sync from OMS (best-effort) ───────────────────────────────────────────────

try:
    new_records = sync_short_picks_from_oms()
    if new_records > 0:
        st.info(f"📡 Synced {new_records} new short-pick record{'s' if new_records != 1 else ''} from OMS.")
except Exception:
    pass  # OMS unavailable — continue with local data


# ── Detail panel ──────────────────────────────────────────────────────────────

def _render_detail_panel(sp_id, role, tab_key, agents):
    sp = get_short_pick_by_id(sp_id)
    if not sp:
        st.error("Short-pick record not found.")
        return

    # Auto-mark in_progress when opened
    if sp["action_status"] == "pending":
        start_short_pick(sp_id)
        sp["action_status"] = "in_progress"

    st.markdown("---")
    left, right = st.columns([1.2, 0.8])

    # ── Right: order context (read-only) ──────────────────────────────────────
    with right:
        st.markdown("#### 📋 Order Context")
        st.markdown(f"**Order ID:** `{sp['order_id']}`")
        st.markdown(f"**Customer:** {sp['customer_name'] or '—'}")
        st.markdown(f"**Phone:** {sp['customer_phone'] or '—'}")
        st.markdown(f"**Amount:** ₹{sp['order_amount']:,.0f}" if sp.get("order_amount") else "**Amount:** —")
        st.markdown(f"**Payment:** {'💳 Prepaid' if sp.get('payment_method') == 'prepaid' else ('💵 COD' if sp.get('payment_method') == 'cod' else sp.get('payment_method') or '—')}")
        st.markdown(f"**Store:** {sp.get('store_code') or '—'}")
        st.markdown(f"**Assigned To:** {sp.get('assigned_agent_name') or '—'}")
        st.markdown(f"**Synced At:** {fmt_dt(sp.get('synced_at'))}")
        if sp.get("started_at"):
            st.markdown(f"**Started At:** {fmt_dt(sp['started_at'])}")
        if sp.get("completed_at"):
            st.markdown(f"**Completed At:** {fmt_dt(sp['completed_at'])}")

        st.markdown("---")
        st.markdown("**Short-Picked Items**")
        if sp.get("short_items"):
            items = [i.strip() for i in sp["short_items"].split(",")]
            skus  = [s.strip() for s in (sp.get("short_skus") or "").split(",")]
            for i, item_name in enumerate(items):
                sku = skus[i] if i < len(skus) else ""
                st.markdown(
                    f"• **{item_name}**" + (f" — `{sku}`" if sku else ""),
                    unsafe_allow_html=True,
                )
        else:
            st.write("—")

        # Admin/Supervisor: reassign
        if has_permission(role, "short_picks", "reassign") and sp["action_status"] != "completed":
            st.markdown("---")
            st.markdown("**Reassign**")
            agent_opts = {a["id"]: a["name"] for a in agents}
            cur_agent  = sp.get("assigned_to")
            default_idx = list(agent_opts.keys()).index(cur_agent) if cur_agent in agent_opts else 0
            new_agent = st.selectbox(
                "Assign to",
                list(agent_opts.keys()),
                format_func=lambda x: agent_opts[x],
                index=default_idx,
                key=f"reassign_{sp_id}_{tab_key}",
            )
            if st.button("Save Assignment", key=f"do_reassign_{sp_id}_{tab_key}"):
                reassign_short_pick(sp_id, new_agent)
                st.success("Reassigned.")
                st.rerun()

    # ── Left: action form ─────────────────────────────────────────────────────
    with left:
        c_close, c_title = st.columns([1, 6])
        with c_close:
            if st.button("✕", key=f"close_{sp_id}_{tab_key}", help="Close panel"):
                st.session_state[f"selected_{tab_key}"] = None
                st.rerun()
        with c_title:
            st.markdown(f"#### SP-{sp_id:03d}")

        st.markdown(status_badge(sp["action_status"]), unsafe_allow_html=True)
        st.markdown("")

        can_act = has_permission(role, "short_picks", "action")
        is_admin_edit = (
            has_permission(role, "short_picks", "reassign")
            and sp["action_status"] == "completed"
        )

        if sp["action_status"] == "completed" and not is_admin_edit:
            # Read-only summary
            st.markdown("**Action outcome**")
            st.markdown(f"- Reached out: **{(sp.get('reached_out') or '—').title()}**")
            st.markdown(f"- Customer response: **{sp.get('customer_response') or '—'}**")
            st.markdown(f"- Resolution: **{sp.get('resolution') or '—'}**")
            if sp.get("notes"):
                st.markdown(f"- Notes: *{sp['notes']}*")
            st.success("Action completed.")

        elif can_act or is_admin_edit:
            pre_reached   = sp.get("reached_out") or "yes"
            pre_response  = sp.get("customer_response") or CUSTOMER_RESPONSES[0]
            pre_resolution = sp.get("resolution") or RESOLUTIONS[0]
            pre_notes     = sp.get("notes") or ""

            reached_options = ["yes", "no", "attempted"]
            reached_labels  = {"yes": "Yes", "no": "No", "attempted": "Attempted"}
            r_idx = reached_options.index(pre_reached) if pre_reached in reached_options else 0

            resp_idx = CUSTOMER_RESPONSES.index(pre_response) if pre_response in CUSTOMER_RESPONSES else 0
            res_idx  = RESOLUTIONS.index(pre_resolution) if pre_resolution in RESOLUTIONS else 0

            reached_out = st.radio(
                "Did you reach out to the customer?",
                reached_options,
                format_func=lambda x: reached_labels[x],
                index=r_idx,
                horizontal=True,
                key=f"reached_{sp_id}_{tab_key}",
            )
            customer_response = st.selectbox(
                "Customer response",
                CUSTOMER_RESPONSES,
                index=resp_idx,
                key=f"response_{sp_id}_{tab_key}",
            )
            resolution = st.selectbox(
                "Resolution taken",
                RESOLUTIONS,
                index=res_idx,
                key=f"resolution_{sp_id}_{tab_key}",
            )
            notes = st.text_area(
                "Notes (optional)",
                value=pre_notes,
                height=80,
                key=f"notes_{sp_id}_{tab_key}",
            )

            col_draft, col_submit = st.columns(2)
            with col_draft:
                if not is_admin_edit:
                    if st.button("💾 Save Draft", key=f"draft_{sp_id}_{tab_key}", use_container_width=True):
                        save_short_pick_draft(sp_id, reached_out, customer_response, resolution, notes)
                        st.info("Draft saved.")
                        st.rerun()
            with col_submit:
                submit_label = "✓ Update" if is_admin_edit else "✓ Submit"
                if st.button(submit_label, key=f"submit_{sp_id}_{tab_key}", type="primary", use_container_width=True):
                    if not reached_out or not customer_response or not resolution:
                        st.error("Please fill all required fields.")
                    else:
                        complete_short_pick_action(sp_id, reached_out, customer_response, resolution, notes)
                        st.success("Action completed!" if not is_admin_edit else "Updated.")
                        st.session_state[f"selected_{tab_key}"] = None
                        st.rerun()

        else:
            st.info("You have view-only access to this module.")
            if sp.get("reached_out"):
                st.markdown(f"- Reached out: **{sp['reached_out'].title()}**")
            if sp.get("customer_response"):
                st.markdown(f"- Customer response: **{sp['customer_response']}**")
            if sp.get("resolution"):
                st.markdown(f"- Resolution: **{sp['resolution']}**")

    st.markdown("---")


# ── Tab renderer ──────────────────────────────────────────────────────────────

def _render_tab(tab_status, role, user, agents, flexi_cols, show_filters=False):
    store_filter = None
    date_from = date_to = None

    if show_filters:
        with st.expander("🔍 Filters", expanded=False):
            f1, f2 = st.columns(2)
            store_filter = f1.text_input("Store code", key=f"store_f_{tab_status}") or None
            date_range = f2.date_input(
                "Date range",
                value=(date.today().replace(day=1), date.today()),
                key=f"date_f_{tab_status}",
            )
            if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
                date_from = str(date_range[0])
                date_to   = str(date_range[1])

    assigned_filter = user.get("id") if role == "agent" else None

    picks = get_short_picks(
        action_status=None if tab_status == "all" else tab_status,
        assigned_to=assigned_filter,
        store=store_filter,
        date_from=date_from,
        date_to=date_to,
    )

    total_val = sum(p.get("order_amount") or 0 for p in picks)
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Records",    len(picks))
    m2.metric("Order Value",      f"₹{total_val:,.0f}")
    m3.metric("Items Short-Picked", sum(p.get("short_item_count") or 0 for p in picks))

    st.divider()

    if not picks:
        st.info("No short-pick records in this category.")
        return

    show_payment = "Payment Method" in flexi_cols
    show_store   = "Store"          in flexi_cols
    show_agent   = "Assigned Agent" in flexi_cols

    col_widths = [0.7, 1.1, 1.4, 1.0, 1.5, 0.8, 1.1]
    col_headers = ["ID", "Order", "Customer", "Amount", "Short Items", "Count", "Status"]
    if show_payment:
        col_widths.append(0.9); col_headers.append("Payment")
    if show_store:
        col_widths.append(0.8); col_headers.append("Store")
    if show_agent:
        col_widths.append(1.3); col_headers.append("Assigned To")
    col_widths.append(0.6); col_headers.append("")

    h = st.columns(col_widths)
    for col, label in zip(h, col_headers):
        col.markdown(f"**{label}**")
    st.markdown('<hr style="margin:2px 0 8px 0">', unsafe_allow_html=True)

    selected_key = f"selected_{tab_status}"
    if selected_key not in st.session_state:
        st.session_state[selected_key] = None

    for p in picks:
        row   = st.columns(col_widths)
        idx   = 0
        items_short = (p.get("short_items") or "—")
        items_display = items_short[:30] + "…" if len(items_short) > 30 else items_short

        row[idx].write(f"SP-{p['id']:03d}"); idx += 1
        row[idx].write(p["order_id"]);       idx += 1
        row[idx].write(p.get("customer_name") or "—"); idx += 1
        row[idx].write(f"₹{p['order_amount']:,.0f}" if p.get("order_amount") else "—"); idx += 1
        row[idx].write(items_display); idx += 1
        row[idx].markdown(item_count_badge(p.get("short_item_count") or 0), unsafe_allow_html=True); idx += 1
        row[idx].markdown(status_badge(p["action_status"]), unsafe_allow_html=True); idx += 1
        if show_payment:
            pm = p.get("payment_method") or "—"
            row[idx].write("💳 Prepaid" if pm == "prepaid" else ("💵 COD" if pm == "cod" else pm)); idx += 1
        if show_store:
            row[idx].write(p.get("store_code") or "—"); idx += 1
        if show_agent:
            row[idx].write(p.get("assigned_agent_name") or "—"); idx += 1

        btn_label = "Close" if st.session_state[selected_key] == p["id"] else "Open"
        if row[idx].button(btn_label, key=f"btn_{p['id']}_{tab_status}"):
            st.session_state[selected_key] = None if st.session_state[selected_key] == p["id"] else p["id"]
            st.rerun()

        if st.session_state[selected_key] == p["id"]:
            _render_detail_panel(p["id"], role, tab_status, agents)


# ── Page ──────────────────────────────────────────────────────────────────────

st.markdown("## ⚠️ Short-Pick Actions")
st.caption("Orders where warehouse short-picked items — contact customers and log resolution.")

agents = get_cx_users(active_only=True)
counts = get_short_pick_counts()

# ── Column picker ─────────────────────────────────────────────────────────────
with st.expander("⚙️ Columns", expanded=False):
    flexi_cols = st.multiselect(
        "Optional columns",
        ["Payment Method", "Store", "Assigned Agent"],
        default=["Store", "Assigned Agent"],
        key="sp_flexi",
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
