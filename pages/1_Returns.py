import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import uuid
import pandas as pd
from datetime import date, datetime
from db.queries import (
    get_returns, get_return_by_id, get_return_items, get_return_counts,
    get_stores, get_cx_users, agent_submit_return, cx_lead_approve, cx_lead_reject,
    wh_send_to_pidge, simulate_pidge_complete, create_return_with_approval,
)
from db.connection import init_db
from utils.rbac import has_permission

init_db()

from utils.page_utils import get_page_user
role, user = get_page_user()

# ── Constants ────────────────────────────────────────────────────────────────

DATA_DIR        = os.path.join(os.path.dirname(__file__), "..", "data")
ORDER_DETAILS_CSV = os.path.join(DATA_DIR, "order_details.csv")

STATUS_LABELS = {
    "pending_action":   "Pending Action",
    "pending_approval": "Pending Approval",
    "pending_pickup":   "Pending Pickup",
    "out_for_pickup":   "Out for Pickup",
    "completed":        "Completed",
    "cancelled":        "Cancelled",
}
STATUS_COLOURS = {
    "pending_action":   "#f0a500",
    "pending_approval": "#e07b00",
    "pending_pickup":   "#1a73e8",
    "out_for_pickup":   "#7b1fa2",
    "completed":        "#2e7d32",
    "cancelled":        "#c62828",
}
SOURCE_CHIPS = {
    "app":         "📱 App",
    "chatbot":     "💬 Chat",
    "admin_panel": "🖥 Admin",
    "cx_portal":   "🖥 CX Portal",
}
TYPE_BADGES = {"return": "↩ Return", "exchange": "🔄 Exchange"}
REFUND_SOURCE_OPTIONS = {"prepaid": ["wallet", "source_refund"], "cod": ["cod_wallet"]}
REFUND_SOURCE_LABELS  = {"wallet": "💳 Wallet", "source_refund": "🏦 Source Refund", "cod_wallet": "💼 COD Wallet"}
REASON_OPTIONS = ["wrong_product", "damaged", "expired", "size_issue", "not_as_expected", "other"]
REASON_LABELS  = {
    "wrong_product":   "Wrong product delivered",
    "damaged":         "Damaged / defective",
    "expired":         "Expired / old manufacturing",
    "size_issue":      "Size / fit issue",
    "not_as_expected": "Not as expected",
    "other":           "Other",
}
SPOKEN_OPTIONS  = ["yes", "no", "attempted"]
SPOKEN_LABELS   = {"yes": "Yes", "no": "No", "attempted": "Attempted"}
PITCHED_OPTIONS = ["yes", "no", "na"]
PITCHED_LABELS  = {"yes": "Yes", "no": "No", "na": "N/A"}
TIME_SLOTS = ["9AM–11AM", "10AM–12PM", "11AM–1PM", "12PM–2PM", "2PM–4PM", "4PM–6PM", "6PM–8PM"]


def fmt_dt(s):
    if not s:
        return "—"
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S").strftime("%d %b %Y, %I:%M %p")
    except Exception:
        return str(s)[:16]


def status_badge(status):
    colour = STATUS_COLOURS.get(status, "#444")
    label  = STATUS_LABELS.get(status, status)
    return f'<span style="background:{colour};color:#fff;padding:2px 9px;border-radius:12px;font-size:0.78rem;font-weight:600">{label}</span>'


@st.cache_data(show_spinner=False)
def load_order_details(path):
    df = pd.read_csv(path, usecols=["order_id", "item_name", "item_sku", "price", "quantity", "Return Amount"], low_memory=False)
    df["order_id"] = df["order_id"].astype(str)
    df["price"] = pd.to_numeric(df["price"], errors="coerce").fillna(0)
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(1).astype(int)
    df["Return Amount"] = pd.to_numeric(df["Return Amount"], errors="coerce").fillna(0)
    return df


# ── Helpers ──────────────────────────────────────────────────────────────────

def _show_readonly_fields(ret):
    if ret.get("type"):
        st.markdown(f"**Type:** {TYPE_BADGES.get(ret['type'], ret['type'].title())}")
    if ret.get("spoken_to_customer"):
        st.markdown(f"**Spoken to customer:** {SPOKEN_LABELS.get(ret['spoken_to_customer'], ret['spoken_to_customer'])}")
    if ret.get("pitched_exchange"):
        st.markdown(f"**Pitched exchange:** {PITCHED_LABELS.get(ret['pitched_exchange'], ret['pitched_exchange'])}")
    if ret.get("reason"):
        st.markdown(f"**Return reason:** {REASON_LABELS.get(ret['reason'], ret['reason'])}")
    if ret.get("refund_source"):
        st.markdown(f"**Refund source:** {REFUND_SOURCE_LABELS.get(ret['refund_source'], ret['refund_source'])}")
    if ret.get("pickup_slot"):
        st.markdown(f"**Pickup slot:** {ret['pickup_slot']}")
    if ret.get("agent_notes"):
        st.markdown(f"**Agent notes:** *{ret['agent_notes']}*")


# ── Detail panel ─────────────────────────────────────────────────────────────

def _render_detail_panel(return_id, role, tab_key):
    ret    = get_return_by_id(return_id)
    items  = get_return_items(return_id)
    stores = get_stores()

    if not ret:
        st.error("Return not found.")
        return

    st.markdown("---")
    left, right = st.columns([1.1, 0.9])

    with right:
        st.markdown("#### 📋 Order Context")
        st.markdown(f"**Order ID:** `{ret['order_id']}`")
        st.markdown(f"**Customer:** {ret['customer_name'] or ret['customer_id']}")
        st.markdown(f"**Phone:** {ret['customer_phone'] or '—'}")
        st.markdown(f"**Payment:** {'💳 Prepaid' if ret['payment_method'] == 'prepaid' else '💵 COD'}")
        st.markdown(f"**Source:** {SOURCE_CHIPS.get(ret['source'], ret['source'])}")
        st.markdown(f"**Type:** {TYPE_BADGES.get(ret['type'], ret['type'])}")
        st.markdown(f"**Created:** {fmt_dt(ret['created_at'])}")

        if items:
            st.markdown("---")
            st.markdown("**Items**")
            for item in items:
                st.markdown(
                    f"• **{item['item_name']}** &nbsp;"
                    f"SKU: `{item['item_sku'] or '—'}` &nbsp;"
                    f"×{item['quantity']} &nbsp; ₹{item['return_amount']:,.2f}",
                    unsafe_allow_html=True,
                )
            total_val = sum(i["return_amount"] for i in items)
            st.markdown(f"**Total: ₹{total_val:,.2f}**")

        if ret.get("pidge_tracking_id"):
            st.markdown("---")
            st.markdown(f"**Pidge ID:** `{ret['pidge_tracking_id']}`")
            st.markdown(f"**Store:** {ret['store_name'] or '—'}")

        if ret.get("rejection_reason"):
            st.warning(f"**Rejection reason:** {ret['rejection_reason']}")

    with left:
        status = ret["status"]
        c_close, c_title = st.columns([1, 5])
        with c_close:
            if st.button("✕", key=f"close_{return_id}_{tab_key}"):
                st.session_state[f"selected_{tab_key}"] = None
                st.rerun()
        with c_title:
            st.markdown(f"#### RET-{return_id:03d}")
        st.markdown(status_badge(status), unsafe_allow_html=True)
        st.markdown("")

        if status == "pending_action" and role in ("agent", "cx_lead", "supervisor", "admin"):
            with st.form(key=f"agent_form_{return_id}"):
                ret_type = st.radio("Type *", ["return", "exchange"], format_func=lambda x: x.title(), horizontal=True)
                payment  = ret["payment_method"] or "prepaid"
                spoken   = st.selectbox("Spoken to customer? *", SPOKEN_OPTIONS, format_func=lambda x: SPOKEN_LABELS[x])
                pitched  = st.selectbox("Pitched exchange? *", PITCHED_OPTIONS, format_func=lambda x: PITCHED_LABELS[x])
                reason   = st.selectbox("Return reason *", REASON_OPTIONS, format_func=lambda x: REASON_LABELS[x])
                ref_opts   = REFUND_SOURCE_OPTIONS.get(payment, ["wallet"])
                refund_src = st.selectbox("Refund source *", ref_opts, format_func=lambda x: REFUND_SOURCE_LABELS[x])
                pickup_date = st.date_input("Pickup date *", min_value=date.today())
                pickup_time = st.selectbox("Pickup time slot *", TIME_SLOTS)
                pickup_slot = f"{pickup_date.strftime('%d %b %Y')}, {pickup_time}"
                notes = st.text_area("Agent notes (optional)", height=80)
                if st.form_submit_button("Submit for Approval →", type="primary"):
                    agent_submit_return(return_id, ret_type, spoken, pitched, reason,
                                        refund_src if ret_type == "return" else None,
                                        pickup_slot, notes)
                    st.success("Submitted for approval!")
                    st.session_state[f"selected_{tab_key}"] = None
                    st.rerun()

        elif status == "pending_approval" and role in ("cx_lead", "supervisor", "admin"):
            st.markdown("**Review**")
            _show_readonly_fields(ret)
            st.markdown("")
            col_a, col_r = st.columns(2)
            with col_a:
                if st.button("✓ Approve", type="primary", key=f"approve_{return_id}_{tab_key}"):
                    cx_lead_approve(return_id)
                    st.success("Approved — moved to Pending Pickup.")
                    st.session_state[f"selected_{tab_key}"] = None
                    st.rerun()
            with col_r:
                with st.expander("✗ Reject"):
                    rej_reason = st.text_area("Rejection reason", key=f"rej_{return_id}_{tab_key}")
                    if st.button("Confirm Reject", key=f"confirm_rej_{return_id}_{tab_key}"):
                        if rej_reason.strip():
                            cx_lead_reject(return_id, rej_reason.strip())
                            st.warning("Rejected — moved to Cancelled.")
                            st.session_state[f"selected_{tab_key}"] = None
                            st.rerun()
                        else:
                            st.error("Please enter a rejection reason.")

        elif status == "pending_approval" and role == "agent":
            st.info("Submitted — awaiting CX Lead approval.")
            _show_readonly_fields(ret)

        elif status == "pending_pickup" and role in ("wh_user", "supervisor", "admin"):
            _show_readonly_fields(ret)
            st.markdown("")
            store_options = {s["id"]: f"{s['name']} — {s['store_code']}" for s in stores}
            selected_store = st.selectbox("Assign dark store", list(store_options.keys()), format_func=lambda x: store_options[x], key=f"store_{return_id}_{tab_key}")
            if st.button("Send to Pidge ↗", type="primary", key=f"pidge_{return_id}_{tab_key}"):
                pidge_id = f"PIDGE-{uuid.uuid4().hex[:8].upper()}"
                wh_send_to_pidge(return_id, selected_store, pidge_id)
                st.success(f"Sent! Pidge ID: `{pidge_id}`")
                st.session_state[f"selected_{tab_key}"] = None
                st.rerun()

        elif status == "pending_pickup":
            _show_readonly_fields(ret)
            st.info("Approved — waiting for warehouse to send to Pidge.")

        elif status == "out_for_pickup":
            _show_readonly_fields(ret)
            st.info(f"Out for pickup. Pidge ID: `{ret['pidge_tracking_id']}`")
            if role in ("admin", "supervisor"):
                st.markdown("---")
                st.caption("🛠 Dev tool")
                if st.button("Simulate Pidge Complete →", key=f"sim_{return_id}_{tab_key}"):
                    simulate_pidge_complete(return_id)
                    st.success("Completed! Refund record auto-created (if return type).")
                    st.session_state[f"selected_{tab_key}"] = None
                    st.rerun()

        else:
            _show_readonly_fields(ret)
            if status == "completed":
                st.success("Return completed. Refund triggered.")
            elif status == "cancelled":
                if ret.get("rejection_reason"):
                    st.error(f"Cancelled: {ret['rejection_reason']}")
                else:
                    st.error("Return cancelled.")

    st.markdown("---")


# ── Manual create return modal ────────────────────────────────────────────────

def _render_manual_create():
    details_df = load_order_details(ORDER_DETAILS_CSV) if os.path.exists(ORDER_DETAILS_CSV) else pd.DataFrame()

    st.markdown("### Create Manual Return")
    order_id = st.text_input("Order ID", placeholder="e.g. 200307")

    selected_items = []
    if order_id.strip() and not details_df.empty:
        order_items = details_df[details_df["order_id"] == order_id.strip()]
        if not order_items.empty:
            item_options = {
                f"{it['item_name']} ({it.get('item_sku','—')}) — ₹{it.get('price',0):,.0f}": {
                    "name": it["item_name"],
                    "sku": str(it.get("item_sku", "")),
                    "qty": int(it.get("quantity", 1)),
                    "unit_price": float(it.get("price", 0)),
                    "return_amount": float(it.get("Return Amount", it.get("price", 0))),
                }
                for _, it in order_items.iterrows()
            }
            sel_labels = st.multiselect("Select items to return", list(item_options.keys()))
            selected_items = [item_options[l] for l in sel_labels]
        else:
            st.caption("No item data found for this order — enter manually below.")

    if not selected_items:
        st.markdown("**Items (manual)**")
        if "manual_ret_items" not in st.session_state:
            st.session_state["manual_ret_items"] = [{"name": "", "sku": "", "qty": 1, "unit_price": 0.0, "return_amount": 0.0}]
        items_list = st.session_state["manual_ret_items"]
        updated = []
        for i, item in enumerate(items_list):
            c1, c2, c3, c4, c5 = st.columns([2.5, 1.5, 0.6, 0.9, 0.5])
            name = c1.text_input("Name", value=item["name"], key=f"mn_{i}", label_visibility="collapsed", placeholder="Item name")
            sku  = c2.text_input("SKU", value=item["sku"], key=f"ms_{i}", label_visibility="collapsed", placeholder="SKU")
            qty  = c3.number_input("Qty", value=item["qty"], min_value=1, key=f"mq_{i}", label_visibility="collapsed")
            up   = c4.number_input("₹", value=float(item["unit_price"]), min_value=0.0, key=f"mp_{i}", label_visibility="collapsed")
            rem  = c5.button("✕", key=f"mr_{i}")
            if not rem:
                updated.append({"name": name, "sku": sku, "qty": qty, "unit_price": up, "return_amount": up * qty})
        if st.button("＋ Add Item", key="manual_add_item"):
            updated.append({"name": "", "sku": "", "qty": 1, "unit_price": 0.0, "return_amount": 0.0})
        st.session_state["manual_ret_items"] = updated
        selected_items = updated

    st.markdown("---")
    customer_phone = st.text_input("Customer phone", placeholder="e.g. 919876543210")
    customer_id    = st.text_input("Customer ID (optional)")
    ret_type   = st.radio("Type", ["return", "exchange"], format_func=lambda x: x.title(), horizontal=True)
    payment    = st.radio("Payment method", ["prepaid", "cod"], format_func=lambda x: x.upper(), horizontal=True)
    spoken     = st.radio("Spoken to customer?", SPOKEN_OPTIONS, format_func=lambda x: SPOKEN_LABELS[x], horizontal=True)
    pitched    = st.radio("Pitched exchange?", PITCHED_OPTIONS, format_func=lambda x: PITCHED_LABELS[x], horizontal=True, disabled=(ret_type == "exchange"))
    reason     = st.selectbox("Return reason", REASON_OPTIONS, format_func=lambda x: REASON_LABELS[x])
    if ret_type == "return":
        ref_opts   = REFUND_SOURCE_OPTIONS.get(payment, ["wallet"])
        refund_src = st.selectbox("Refund source", ref_opts, format_func=lambda x: REFUND_SOURCE_LABELS[x])
    else:
        refund_src = None
        st.info("Exchange — no refund source required.")
    pickup_date = st.date_input("Pickup date", min_value=date.today())
    pickup_time = st.selectbox("Pickup time slot", TIME_SLOTS)
    pickup_slot = f"{pickup_date.strftime('%d %b %Y')}, {pickup_time}"
    notes = st.text_area("Notes (optional)", height=80)

    b1, b2 = st.columns(2)
    if b1.button("Cancel", key="manual_cancel"):
        st.session_state["show_manual_create"] = False
        st.session_state.pop("manual_ret_items", None)
        st.rerun()
    if b2.button("✓ Submit Return", key="manual_submit", type="primary"):
        valid = [it for it in selected_items if str(it.get("name", "")).strip()]
        if not order_id.strip():
            st.error("Enter an Order ID.")
        elif not valid:
            st.error("Add at least one item.")
        else:
            new_id = create_return_with_approval(
                order_id=order_id.strip(),
                customer_id=customer_id.strip() or "",
                customer_phone=customer_phone.strip(),
                payment_method=payment,
                ret_type=ret_type,
                items=valid,
                spoken=spoken,
                pitched=pitched if ret_type == "return" else "na",
                reason=reason,
                refund_source=refund_src,
                pickup_slot=pickup_slot,
                notes=notes,
                agent_id=user.get("id"),
                source="cx_portal",
            )
            st.success(f"Return RET-{new_id:03d} created — now in Pending Approval.")
            st.session_state["show_manual_create"] = False
            st.session_state.pop("manual_ret_items", None)
            st.rerun()


# ── Tab renderer ──────────────────────────────────────────────────────────────

def _render_tab(status_key, role):
    # ── Filters ──────────────────────────────────────────────────────────────
    with st.expander("🔍 Filters", expanded=False):
        stores_list = get_stores()
        agents_list = [u for u in get_cx_users(active_only=True) if u["role"] in ("agent", "cx_lead", "supervisor", "admin")]

        f1, f2, f3 = st.columns(3)
        customer_search = f1.text_input("Customer name / phone", key=f"cust_f_{status_key}", placeholder="Search…")
        store_opts      = {"": "All Stores"} | {str(s["id"]): s["name"] for s in stores_list}
        sel_store       = f2.selectbox("Store", list(store_opts.keys()), format_func=lambda x: store_opts[x], key=f"store_f_{status_key}")
        agent_opts      = {"": "All Agents"} | {str(a["id"]): a["name"] for a in agents_list}
        sel_agent       = f3.selectbox("Agent", list(agent_opts.keys()), format_func=lambda x: agent_opts[x], key=f"agent_f_{status_key}")

        f4, f5, f6 = st.columns(3)
        type_opts   = {"": "All Types", "return": "↩ Return", "exchange": "🔄 Exchange"}
        sel_type    = f4.selectbox("Type", list(type_opts.keys()), format_func=lambda x: type_opts[x], key=f"type_f_{status_key}")
        source_opts = {"": "All Sources", "app": "App", "chatbot": "Chatbot", "admin_panel": "Admin Panel", "cx_portal": "CX Portal"}
        sel_source  = f5.selectbox("Source", list(source_opts.keys()), format_func=lambda x: source_opts[x], key=f"src_f_{status_key}")
        pay_opts    = {"": "All", "prepaid": "Prepaid", "cod": "COD"}
        sel_pay     = f6.selectbox("Payment", list(pay_opts.keys()), format_func=lambda x: pay_opts[x], key=f"pay_f_{status_key}")

        f7, f8 = st.columns(2)
        date_from = f7.date_input("From date", value=None, key=f"df_{status_key}")
        date_to   = f8.date_input("To date",   value=None, key=f"dt_{status_key}")

    returns = get_returns(
        status_filter   = None if status_key == "all" else status_key,
        store_id        = int(sel_store) if sel_store else None,
        agent_id        = int(sel_agent) if sel_agent else None,
        customer_search = customer_search or None,
        date_from       = str(date_from) if date_from else None,
        date_to         = str(date_to) if date_to else None,
        type_filter     = sel_type or None,
        source_filter   = sel_source or None,
        payment_filter  = sel_pay or None,
    )

    today_str      = date.today().strftime("%Y-%m-%d")
    today_count    = sum(1 for r in returns if (r.get("created_at") or "").startswith(today_str))
    total_value    = sum(r["total_return_value"] for r in returns)
    return_count   = sum(1 for r in returns if r["type"] == "return")
    exchange_count = sum(1 for r in returns if r["type"] == "exchange")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total", len(returns))
    m2.metric("Return Value", f"₹{total_value:,.0f}")
    m3.metric("Today", today_count)
    m4.metric("Returns / Exchanges", f"{return_count} / {exchange_count}")

    st.divider()

    if not returns:
        st.info("No returns match these filters.")
        return

    h = st.columns([0.7, 1.1, 1.5, 1.0, 1.0, 0.6, 1.0, 1.1, 1.3, 0.7])
    for col, label in zip(h, ["ID", "Order", "Customer", "Type", "Source", "Items", "Value", "Agent", "Created", ""]):
        col.markdown(f"**{label}**")
    st.markdown('<hr style="margin:2px 0 8px 0">', unsafe_allow_html=True)

    selected_key = f"selected_{status_key}"
    if selected_key not in st.session_state:
        st.session_state[selected_key] = None

    for r in returns:
        row = st.columns([0.7, 1.1, 1.5, 1.0, 1.0, 0.6, 1.0, 1.1, 1.3, 0.7])
        row[0].write(f"RET-{r['id']:03d}")
        row[1].write(r["order_id"])
        row[2].write(r.get("customer_name") or r["customer_id"])
        row[3].write(TYPE_BADGES.get(r["type"], r["type"]))
        row[4].write(SOURCE_CHIPS.get(r["source"], r["source"]))
        row[5].write(str(r["item_count"]))
        row[6].write(f"₹{r['total_return_value']:,.0f}")
        row[7].write(r.get("agent_name") or "—")
        row[8].write(fmt_dt(r["created_at"])[:11])

        btn_label = "Close" if st.session_state[selected_key] == r["id"] else "Open"
        if row[9].button(btn_label, key=f"btn_{r['id']}_{status_key}"):
            st.session_state[selected_key] = None if st.session_state[selected_key] == r["id"] else r["id"]
            st.rerun()

        if st.session_state[selected_key] == r["id"]:
            _render_detail_panel(r["id"], role, status_key)


# ── Page header ───────────────────────────────────────────────────────────────

h_col, btn_col = st.columns([3, 1])
with h_col:
    st.markdown("## 📦 Returns & Exchanges")
with btn_col:
    if has_permission(role, "returns", "create"):
        if st.button("＋ Create Manual Return", key="open_manual_create", use_container_width=True):
            st.session_state["show_manual_create"] = not st.session_state.get("show_manual_create", False)
            st.rerun()

if st.session_state.get("show_manual_create", False):
    with st.container(border=True):
        _render_manual_create()
    st.markdown("")

counts = get_return_counts()
total  = sum(counts.values())

tab_defs = [
    ("all",              f"All  ({total})"),
    ("pending_action",   f"Pending Action  ({counts.get('pending_action', 0)})"),
    ("pending_approval", f"Pending Approval  ({counts.get('pending_approval', 0)})"),
    ("pending_pickup",   f"Pending Pickup  ({counts.get('pending_pickup', 0)})"),
    ("out_for_pickup",   f"Out for Pickup  ({counts.get('out_for_pickup', 0)})"),
    ("completed",        f"Completed  ({counts.get('completed', 0)})"),
    ("cancelled",        f"Cancelled  ({counts.get('cancelled', 0)})"),
]

tabs = st.tabs([label for _, label in tab_defs])
for tab_obj, (status_key, _) in zip(tabs, tab_defs):
    with tab_obj:
        _render_tab(status_key, role)
