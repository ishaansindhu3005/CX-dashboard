import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
from datetime import date
from db.connection import init_db
from db.queries import check_return_exists, create_return_with_approval
from utils.rbac import has_permission

init_db()

from utils.page_utils import get_page_user
role, user = get_page_user()

if not has_permission(role, "orders", "view"):
    st.error("🚫 Access Denied.")
    st.stop()

# ── Constants ─────────────────────────────────────────────────────────────────

DATA_DIR            = os.path.join(os.path.dirname(__file__), "..", "data")
ORDERS_CSV          = os.path.join(DATA_DIR, "orders.csv")
ORDER_DETAILS_CSV   = os.path.join(DATA_DIR, "order_details.csv")

ORDERS_COLS = [
    "id", "user_id", "contact_person_number",
    "order_amount", "coupon_code", "coupon_discount_amount",
    "order_status", "created_at", "Is Return", "return_amount",
    "FINAL STORE", "NEW_REPEAT", "is_try_and_buy",
]
DETAILS_COLS = [
    "order_id", "item_name", "item_sku", "price", "quantity",
    "is_return", "Return Amount", "store_id", "Brand",
    "SellingPriceX_Quantity", "discount_on_item", "is_rx",
]

ORDER_STATUS_COLOURS = {
    "delivered":            "#2e7d32",
    "cancelled":            "#c62828",
    "canceled":             "#c62828",
    "failed":               "#991b1b",
    "undelivered":          "#ea580c",
    "pending":              "#f0a500",
    "confirmed":            "#1a73e8",
    "rto_out_for_delivery": "#7b1fa2",
    "rto_delivered":        "#6d28d9",
}

RETURN_STATUS_COLOURS = {
    "pending_action":   "#f0a500",
    "pending_approval": "#e07b00",
    "pending_pickup":   "#1a73e8",
    "out_for_pickup":   "#7b1fa2",
    "completed":        "#2e7d32",
    "cancelled":        "#c62828",
}
RETURN_STATUS_LABELS = {
    "pending_action":   "Pending Action",
    "pending_approval": "Pending Approval",
    "pending_pickup":   "Pending Pickup",
    "out_for_pickup":   "Out for Pickup",
    "completed":        "Completed",
    "cancelled":        "Cancelled",
}

SPOKEN_OPTIONS  = ["yes", "no", "attempted"]
SPOKEN_LABELS   = {"yes": "Yes", "no": "No", "attempted": "Attempted"}
PITCHED_OPTIONS = ["yes", "no", "na"]
PITCHED_LABELS  = {"yes": "Yes", "no": "No", "na": "N/A"}
REASON_OPTIONS  = ["wrong_product", "damaged", "expired", "size_issue", "not_as_expected", "other"]
REASON_LABELS   = {
    "wrong_product":   "Wrong product delivered",
    "damaged":         "Damaged / defective",
    "expired":         "Expired / old manufacturing",
    "size_issue":      "Size / fit issue",
    "not_as_expected": "Not as expected",
    "other":           "Other",
}
REFUND_SOURCE_OPTIONS = {"prepaid": ["wallet", "source_refund"], "cod": ["cod_wallet"]}
REFUND_SOURCE_LABELS  = {"wallet": "💳 Wallet", "source_refund": "🏦 Source Refund", "cod_wallet": "💼 COD Wallet"}
TIME_SLOTS = ["9AM–11AM", "10AM–12PM", "11AM–1PM", "12PM–2PM", "2PM–4PM", "4PM–6PM", "6PM–8PM"]


def pill(label, colour):
    return (
        f'<span style="background:{colour};color:#fff;padding:2px 9px;'
        f'border-radius:12px;font-size:0.78rem;font-weight:600">{label}</span>'
    )


def fmt_dt(s):
    if not s or (hasattr(s, '__class__') and s.__class__.__name__ == 'NaTType'):
        return "—"
    try:
        return pd.to_datetime(s).strftime("%d %b %Y, %I:%M %p")
    except Exception:
        return str(s)


# ── CSV loaders ───────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def load_orders(path: str) -> pd.DataFrame:
    available = pd.read_csv(path, nrows=0).columns.tolist()
    cols = [c for c in ORDERS_COLS if c in available]
    df = pd.read_csv(path, usecols=cols, low_memory=False)
    df["id"] = df["id"].astype(str)
    df["user_id"] = df["user_id"].astype(str)
    df["contact_person_number"] = df["contact_person_number"].astype(str)
    df["Is Return"] = pd.to_numeric(df.get("Is Return", 0), errors="coerce").fillna(0).astype(int)
    df["order_amount"] = pd.to_numeric(df.get("order_amount", 0), errors="coerce").fillna(0)
    df["return_amount"] = pd.to_numeric(df.get("return_amount", 0), errors="coerce").fillna(0)
    df["coupon_discount_amount"] = pd.to_numeric(df.get("coupon_discount_amount", 0), errors="coerce").fillna(0)
    df["is_try_and_buy"] = pd.to_numeric(df.get("is_try_and_buy", 0), errors="coerce").fillna(0).astype(int)
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
    return df


@st.cache_data(show_spinner=False)
def load_order_details(path: str) -> pd.DataFrame:
    available = pd.read_csv(path, nrows=0).columns.tolist()
    cols = [c for c in DETAILS_COLS if c in available]
    df = pd.read_csv(path, usecols=cols, low_memory=False)
    df["order_id"] = df["order_id"].astype(str)
    df["price"] = pd.to_numeric(df.get("price", 0), errors="coerce").fillna(0)
    df["quantity"] = pd.to_numeric(df.get("quantity", 1), errors="coerce").fillna(1).astype(int)
    df["Return Amount"] = pd.to_numeric(df.get("Return Amount", 0), errors="coerce").fillna(0)
    return df


# ── Page header + CSV upload ──────────────────────────────────────────────────

h_col, upload_col = st.columns([3, 1])
with h_col:
    st.markdown("## 📋 Orders")
with upload_col:
    uploaded = st.file_uploader("Upload Orders CSV", type=["csv"], label_visibility="collapsed", key="order_csv_up")
    if uploaded:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(ORDERS_CSV, "wb") as f:
            f.write(uploaded.read())
        load_orders.clear()
        st.success("CSV updated.")
        st.rerun()

if not os.path.exists(ORDERS_CSV):
    st.info("No orders data. Upload a CSV above.")
    st.stop()

df = load_orders(ORDERS_CSV)
details_df = load_order_details(ORDER_DETAILS_CSV) if os.path.exists(ORDER_DETAILS_CSV) else pd.DataFrame()

# ── Filters ───────────────────────────────────────────────────────────────────

fc1, fc2, fc3, fc4, fc5 = st.columns([2, 1.2, 1.2, 1.0, 0.8])
search       = fc1.text_input("Search", placeholder="Order ID or phone", label_visibility="collapsed")
statuses     = ["All"] + sorted(df["order_status"].dropna().unique().tolist())
stores       = ["All"] + sorted(df["FINAL STORE"].dropna().unique().tolist())
sel_status   = fc2.selectbox("Status", statuses, label_visibility="collapsed")
sel_store    = fc3.selectbox("Store", stores, label_visibility="collapsed")
sort_options = {"Newest first": ("created_at", False), "Oldest first": ("created_at", True), "Amount ↓": ("order_amount", False), "Amount ↑": ("order_amount", True)}
sel_sort     = fc4.selectbox("Sort", list(sort_options.keys()), label_visibility="collapsed")
returns_only = fc5.checkbox("Returns only")

filtered = df.copy()
if search:
    s = search.strip().lower()
    filtered = filtered[
        filtered["id"].str.lower().str.contains(s, na=False) |
        filtered["contact_person_number"].str.lower().str.contains(s, na=False)
    ]
if sel_status != "All":
    filtered = filtered[filtered["order_status"] == sel_status]
if sel_store != "All":
    filtered = filtered[filtered["FINAL STORE"] == sel_store]
if returns_only:
    filtered = filtered[filtered["Is Return"] == 1]

sort_col, sort_asc = sort_options[sel_sort]
filtered = filtered.sort_values(sort_col, ascending=sort_asc, na_position="last")

st.caption(f"{len(filtered):,} orders")

# ── Pagination helpers ────────────────────────────────────────────────────────

PAGE_SIZE   = 50
total_pages = max(1, (len(filtered) - 1) // PAGE_SIZE + 1)

def _page_nav(key_suffix):
    p1, p2, p3 = st.columns([1, 2, 1])
    cur = st.session_state.get("orders_page", 1)
    if p1.button("← Prev", key=f"prev_{key_suffix}", disabled=(cur <= 1)):
        st.session_state["orders_page"] = cur - 1
        st.rerun()
    p2.markdown(f"<div style='text-align:center;padding-top:6px'>Page {cur} of {total_pages}</div>", unsafe_allow_html=True)
    if p3.button("Next →", key=f"next_{key_suffix}", disabled=(cur >= total_pages)):
        st.session_state["orders_page"] = cur + 1
        st.rerun()

if "orders_page" not in st.session_state:
    st.session_state["orders_page"] = 1
# Clamp page if filters reduced results
if st.session_state["orders_page"] > total_pages:
    st.session_state["orders_page"] = 1

page    = st.session_state["orders_page"]
start   = (page - 1) * PAGE_SIZE
page_df = filtered.iloc[start : start + PAGE_SIZE]

_page_nav("top")

# ── Orders table via st.dataframe ────────────────────────────────────────────

def _status_label(s):
    return s.replace("_", " ").title() if s else "—"

display_df = page_df[[
    "id", "contact_person_number", "order_amount", "order_status",
    "FINAL STORE", "Is Return", "created_at", "coupon_code",
]].copy()
display_df.columns = ["Order ID", "Phone", "Amount (₹)", "Status", "Store", "Return", "Date", "Coupon"]
display_df["Status"] = display_df["Status"].apply(_status_label)
display_df["Return"] = display_df["Return"].apply(lambda x: "↩ Yes" if int(x) == 1 else "—")
display_df["Coupon"] = display_df["Coupon"].apply(lambda x: "—" if str(x) in ("nan", "NoCouponApplied", "", "None") else str(x))
display_df["Date"] = pd.to_datetime(display_df["Date"], errors="coerce").dt.strftime("%d %b %Y")

if "order_selected" not in st.session_state:
    st.session_state["order_selected"] = None

event = st.dataframe(
    display_df,
    column_config={
        "Amount (₹)": st.column_config.NumberColumn("Amount (₹)", format="₹%.0f"),
        "Date": st.column_config.TextColumn("Date"),
    },
    selection_mode="single-row",
    on_select="rerun",
    use_container_width=True,
    hide_index=True,
    key=f"orders_df_{page}",
)

sel_rows = event.selection.rows if event.selection.rows else []
if sel_rows:
    new_id = str(page_df.iloc[sel_rows[0]]["id"])
    if new_id != st.session_state.get("order_selected"):
        # Clear return form state when switching order
        for k in list(st.session_state.keys()):
            if k.startswith("ret_form_") or k == "ret_items" or k.startswith("ret_sel_"):
                del st.session_state[k]
        st.session_state["order_selected"] = new_id

# If a row is selected, show detail panel below
if st.session_state.get("order_selected"):
    order_id = st.session_state["order_selected"]
    # Find the row in the full filtered df
    row_matches = filtered[filtered["id"] == order_id]
    if row_matches.empty:
        # Not found in current filtered/page view — just clear selection
        st.session_state["order_selected"] = None
    else:
        row = row_matches.iloc[0]
        phone    = str(row.get("contact_person_number", "—"))
        amount   = row.get("order_amount", 0)
        coupon   = str(row.get("coupon_code", "") or "")
        if coupon in ("nan", "NoCouponApplied", ""):
            coupon = "—"
        status   = str(row.get("order_status", "—"))
        store    = str(row.get("FINAL STORE", "—"))
        is_ret   = int(row.get("Is Return", 0))
        created  = row.get("created_at", "")

        with st.container(border=True):
            # ── Header row ────────────────────────────────────────────────────────
            hd1, hd2, hd3, hd4, hd5, hd6, hd7 = st.columns([0.5, 1.2, 1.5, 1.2, 1.2, 1.5, 0.6])
            if hd1.button("✕ Close", key=f"close_ord_{order_id}"):
                st.session_state["order_selected"] = None
                st.rerun()
            hd2.markdown(f"**Order #{order_id}**")
            hd3.markdown(f"📞 `{phone}`")
            hd4.markdown(f"🏪 {store}")
            hd5.markdown(f"🗓 {fmt_dt(created)[:11]}")
            hd6.markdown(
                f"**₹{amount:,.0f}**" +
                (f"  `{coupon}` −₹{row.get('coupon_discount_amount',0):,.0f}" if coupon != "—" else ""),
            )
            hd7.markdown(
                pill(status.replace("_", " ").title(), ORDER_STATUS_COLOURS.get(status.lower(), "#64748b")),
                unsafe_allow_html=True,
            )

            # ── Order info + CX actions row ───────────────────────────────────────
            order_items_all = details_df[details_df["order_id"] == order_id] if not details_df.empty else pd.DataFrame()

            nr = str(row.get("NEW_REPEAT", "—"))
            tags_html = ""
            if nr == "NEW":    tags_html += '<span style="background:#dbeafe;color:#1d4ed8;padding:2px 8px;border-radius:8px;font-size:0.75rem;font-weight:600;margin-right:4px">🆕 New</span>'
            if nr == "REPEAT": tags_html += '<span style="background:#dcfce7;color:#166534;padding:2px 8px;border-radius:8px;font-size:0.75rem;font-weight:600;margin-right:4px">🔄 Repeat</span>'
            if int(row.get("is_try_and_buy", 0)): tags_html += '<span style="background:#fef3c7;color:#92400e;padding:2px 8px;border-radius:8px;font-size:0.75rem;font-weight:600;margin-right:4px">🛍 T&B</span>'

            info_l, info_r = st.columns([1, 1.2])
            with info_l:
                coupon_html = ""
                if coupon != "—":
                    coupon_html = f'<code style="font-size:0.78rem">{coupon}</code> <span style="color:#dc2626;font-size:0.78rem">−₹{row.get("coupon_discount_amount",0):,.0f}</span>'
                else:
                    coupon_html = '<span style="color:#94a3b8">None</span>'
                st.markdown(
                    f'<div style="background:#faf5ff;border:1px solid #ede9fe;border-radius:10px;padding:12px 16px">'
                    f'<div style="font-size:0.72rem;font-weight:700;color:#6d28d9;text-transform:uppercase;letter-spacing:.07em;margin-bottom:6px">Order Info</div>'
                    f'<div style="font-size:0.83rem;color:#334155;line-height:1.9">'
                    f'<b>Coupon:</b> {coupon_html}<br>'
                    f'<b>User ID:</b> {row.get("user_id","—")}<br>'
                    f'<b>Store:</b> {store}'
                    + (f'<br>{tags_html}' if tags_html else "")
                    + f'</div></div>',
                    unsafe_allow_html=True,
                )
            with info_r:
                existing_ret = check_return_exists(order_id)
                if existing_ret:
                    r_st    = existing_ret["status"]
                    r_colour = RETURN_STATUS_COLOURS.get(r_st, "#444")
                    r_label  = RETURN_STATUS_LABELS.get(r_st, r_st)
                    st.markdown(
                        f'<div style="background:#fff7ed;border:1px solid #fed7aa;border-radius:10px;padding:12px 16px">'
                        f'<div style="font-size:0.72rem;font-weight:700;color:#ea580c;text-transform:uppercase;letter-spacing:.07em;margin-bottom:6px">CX Actions</div>'
                        f'Return: {pill(r_label, r_colour)}<br>'
                        f'<span style="color:#64748b;font-size:0.78rem">Go to Returns module to manage.</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                elif status.lower() == "delivered" and has_permission(role, "returns", "create"):
                    show_key = f"ret_form_{order_id}"
                    if show_key not in st.session_state:
                        st.session_state[show_key] = False

                    if not st.session_state[show_key]:
                        st.markdown(
                            '<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;padding:12px 16px">'
                            '<div style="font-size:0.72rem;font-weight:700;color:#16a34a;text-transform:uppercase;letter-spacing:.07em;margin-bottom:8px">CX Actions</div>',
                            unsafe_allow_html=True,
                        )
                        if st.button("↩ Return Item(s)", key=f"init_ret_{order_id}", type="primary"):
                            st.session_state[show_key] = True
                            st.rerun()
                        st.markdown("</div>", unsafe_allow_html=True)
                    else:
                        st.markdown("**↩ Initiate Return**")

                        if not order_items_all.empty:
                            item_options = {
                                f"{it['item_name']} — ₹{it.get('price',0):,.0f}": {
                                    "name": it["item_name"],
                                    "sku": str(it.get("item_sku", "")),
                                    "qty": int(it.get("quantity", 1)),
                                    "unit_price": float(it.get("price", 0)),
                                    "return_amount": float(it.get("Return Amount", it.get("price", 0))),
                                }
                                for _, it in order_items_all.iterrows()
                            }
                        else:
                            item_options = {}

                        if item_options:
                            sel_labels     = st.multiselect("Select items *", list(item_options.keys()), key=f"ret_sel_{order_id}")
                            selected_items = [item_options[l] for l in sel_labels]
                        else:
                            st.caption("No item data — enter manually.")
                            if "ret_items" not in st.session_state:
                                st.session_state["ret_items"] = [{"name": "", "sku": "", "qty": 1, "unit_price": 0.0, "return_amount": 0.0}]
                            items_list = st.session_state["ret_items"]
                            updated = []
                            for i, item in enumerate(items_list):
                                ic1, ic2, ic3, ic4, ic5 = st.columns([2.5, 1.5, 0.6, 0.9, 0.5])
                                name = ic1.text_input("Name", value=item["name"], key=f"iname_{order_id}_{i}", label_visibility="collapsed", placeholder="Item name")
                                sku  = ic2.text_input("SKU",  value=item["sku"],  key=f"isku_{order_id}_{i}",  label_visibility="collapsed", placeholder="SKU")
                                qty  = ic3.number_input("Qty", value=item["qty"], min_value=1, key=f"iqty_{order_id}_{i}", label_visibility="collapsed")
                                up   = ic4.number_input("₹", value=float(item["unit_price"]), min_value=0.0, key=f"iprice_{order_id}_{i}", label_visibility="collapsed")
                                if not ic5.button("✕", key=f"irem_{order_id}_{i}"):
                                    updated.append({"name": name, "sku": sku, "qty": qty, "unit_price": up, "return_amount": up * qty})
                            if st.button("＋ Add Item", key=f"iadd_{order_id}"):
                                updated.append({"name": "", "sku": "", "qty": 1, "unit_price": 0.0, "return_amount": 0.0})
                            st.session_state["ret_items"] = updated
                            selected_items = updated

                        if selected_items or not item_options:
                            ret_type = st.radio("Type *", ["return", "exchange"], format_func=lambda x: x.title(), horizontal=True, key=f"rtype_{order_id}")
                            payment  = st.radio("Payment *", ["prepaid", "cod"], format_func=lambda x: x.upper(), horizontal=True, key=f"rpay_{order_id}")
                            spoken   = st.radio("Spoken to customer? *", SPOKEN_OPTIONS, format_func=lambda x: SPOKEN_LABELS[x], horizontal=True, key=f"rspoken_{order_id}")
                            pitched  = st.radio("Pitched exchange? *", PITCHED_OPTIONS, format_func=lambda x: PITCHED_LABELS[x], horizontal=True, key=f"rpitched_{order_id}")
                            reason   = st.selectbox("Return reason *", REASON_OPTIONS, format_func=lambda x: REASON_LABELS[x], key=f"rreason_{order_id}")
                            if ret_type == "return":
                                ref_opts   = REFUND_SOURCE_OPTIONS.get(payment, ["wallet"])
                                refund_src = st.selectbox("Refund source *", ref_opts, format_func=lambda x: REFUND_SOURCE_LABELS[x], key=f"rrefsrc_{order_id}")
                            else:
                                refund_src = None
                                st.info("Exchange — no refund source.")
                            pickup_date = st.date_input("Pickup date *", min_value=date.today(), key=f"rpdate_{order_id}")
                            pickup_time = st.selectbox("Pickup time *", TIME_SLOTS, key=f"rptime_{order_id}")
                            pickup_slot = f"{pickup_date.strftime('%d %b %Y')}, {pickup_time}"
                            notes = st.text_area("Notes", height=60, key=f"rnotes_{order_id}")

                            bc, bs = st.columns(2)
                            if bc.button("Cancel", key=f"rcancel_{order_id}"):
                                st.session_state[show_key] = False
                                st.rerun()
                            if bs.button("✓ Submit", key=f"rsubmit_{order_id}", type="primary"):
                                items_to_use = selected_items if item_options else st.session_state.get("ret_items", [])
                                valid = [it for it in items_to_use if str(it.get("name", "")).strip()]
                                if not valid:
                                    st.error("Select at least one item.")
                                else:
                                    new_id = create_return_with_approval(
                                        order_id=order_id,
                                        customer_id=str(row.get("user_id", "")),
                                        customer_phone=phone,
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
                                    st.success(f"RET-{new_id:03d} → Pending Approval.")
                                    st.session_state[show_key] = False
                                    st.session_state.pop("ret_items", None)
                                    st.rerun()

                elif status.lower() != "delivered":
                    st.markdown(
                        '<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:12px 16px">'
                        '<div style="font-size:0.72rem;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:.07em;margin-bottom:4px">CX Actions</div>'
                        '<span style="color:#64748b;font-size:0.83rem">Returns only available for delivered orders.</span>'
                        '</div>',
                        unsafe_allow_html=True,
                    )

            st.markdown('<div style="margin-top:12px"></div>', unsafe_allow_html=True)

            # ── Items table (full-width, admin-panel style) ───────────────────────
            if not order_items_all.empty:
                if "store_id" in order_items_all.columns:
                    store_ids = sorted(order_items_all["store_id"].dropna().unique().tolist())
                else:
                    store_ids = ["—"]

                # Use FINAL STORE name for tab labels
                if len(store_ids) == 1:
                    tab_labels = [store]
                else:
                    tab_labels = [f"{store} · Part {i+1}" for i, _ in enumerate(store_ids)]

                store_tabs = st.tabs(tab_labels)

                for tab_obj, sid in zip(store_tabs, store_ids):
                    with tab_obj:
                        if "store_id" in order_items_all.columns and sid != "—":
                            grp = order_items_all[order_items_all["store_id"] == sid]
                        else:
                            grp = order_items_all

                        # Header
                        th = st.columns([0.3, 3.8, 1.1, 0.4, 0.8, 0.9, 0.85, 0.85])
                        for col, lbl in zip(th, ["#", "Item Details", "SKU", "Qty", "Price", "Sell Price", "Discount", "Status"]):
                            col.markdown(
                                f'<span style="font-size:0.72rem;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:.07em">{lbl}</span>',
                                unsafe_allow_html=True,
                            )
                        st.markdown('<hr style="margin:4px 0 6px 0;border-color:#ede9fe">', unsafe_allow_html=True)

                        for i, (_, it) in enumerate(grp.iterrows(), 1):
                            tr = st.columns([0.3, 3.8, 1.1, 0.4, 0.8, 0.9, 0.85, 0.85])
                            tr[0].markdown(f'<span style="color:#94a3b8;font-size:0.85rem">{i}</span>', unsafe_allow_html=True)
                            brand = str(it.get("Brand", "") or "")
                            name  = str(it.get("item_name", ""))
                            qty_v = int(it.get("quantity", 1))
                            tr[1].markdown(
                                f'<div style="line-height:1.4">'
                                f'<span style="font-weight:600;font-size:0.85rem">{name}</span>'
                                + (f'<br><span style="font-size:0.72rem;color:#94a3b8">{brand}</span>' if brand else "")
                                + f'<br><span style="font-size:0.72rem;color:#64748b">1 × ₹{it.get("price",0):,.0f}</span>'
                                + f'</div>',
                                unsafe_allow_html=True,
                            )
                            tr[2].markdown(
                                f'<code style="font-size:0.72rem;background:#f1f5f9;padding:2px 5px;border-radius:4px">{it.get("item_sku","—")}</code>',
                                unsafe_allow_html=True,
                            )
                            tr[3].markdown(f'<span style="font-size:0.85rem">{qty_v}</span>', unsafe_allow_html=True)
                            tr[4].markdown(f'<span style="font-size:0.85rem">₹{it.get("price",0):,.0f}</span>', unsafe_allow_html=True)
                            spxq = float(it.get("SellingPriceX_Quantity", 0) or 0)
                            sell = spxq / qty_v if spxq and qty_v else float(it.get("price", 0))
                            tr[5].markdown(f'<span style="font-size:0.85rem">₹{sell:,.0f}</span>', unsafe_allow_html=True)
                            disc = float(it.get("discount_on_item", 0) or 0)
                            disc_html = f'<span style="color:#dc2626;font-size:0.85rem">−₹{disc:,.0f}</span>' if disc else '<span style="color:#94a3b8;font-size:0.85rem">—</span>'
                            tr[6].markdown(disc_html, unsafe_allow_html=True)
                            is_ret_item = int(it.get("is_return", 0))
                            is_rx       = int(it.get("is_rx", 0))
                            if is_ret_item:
                                tr[7].markdown(
                                    '<span style="background:#fee2e2;color:#c62828;padding:2px 7px;border-radius:8px;font-size:0.72rem;font-weight:600">↩ Returned</span>',
                                    unsafe_allow_html=True,
                                )
                            elif is_rx:
                                tr[7].markdown(
                                    '<span style="background:#ede9fe;color:#6d28d9;padding:2px 7px;border-radius:8px;font-size:0.72rem;font-weight:600">Rx</span>',
                                    unsafe_allow_html=True,
                                )
                            else:
                                tr[7].markdown('<span style="color:#94a3b8;font-size:0.85rem">—</span>', unsafe_allow_html=True)

                        st.markdown('<hr style="margin:6px 0 0 0;border-color:#ede9fe">', unsafe_allow_html=True)
            else:
                st.info("No item data available for this order.")

_page_nav("bottom")
