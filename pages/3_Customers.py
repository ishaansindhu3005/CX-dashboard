import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
from db.connection import init_db
from db.queries import get_returns_for_customer, get_crm_calls_for_customer, get_wallet_credits_for_customer
from utils.rbac import has_permission

init_db()

from utils.page_utils import get_page_user
role, user = get_page_user()

if not has_permission(role, "customers", "view"):
    st.error("🚫 Access Denied — you don't have permission to view this module.")
    st.stop()

# ── Constants ─────────────────────────────────────────────────────────────────

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
CSV_PATH = os.path.join(DATA_DIR, "orders.csv")

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
CRM_COLOURS = {"pending": "#f0a500", "in_progress": "#1a73e8", "completed": "#2e7d32"}


def pill(label, colour):
    return (
        f'<span style="background:{colour};color:#fff;padding:2px 8px;'
        f'border-radius:10px;font-size:0.75rem;font-weight:600">{label}</span>'
    )


def coupon_pill(code):
    return (
        f'<span style="background:#e2e8f0;color:#334155;padding:1px 8px;'
        f'border-radius:8px;font-size:0.78rem;font-weight:500;margin-right:4px">{code}</span>'
    )


def fmt_dt(s):
    if not s or pd.isna(s):
        return "—"
    try:
        return pd.to_datetime(s).strftime("%d %b %Y")
    except Exception:
        return str(s)


# ── CSV loading ───────────────────────────────────────────────────────────────

COLS_LOAD = [
    "id", "user_id", "contact_person_number",
    "order_amount", "coupon_code",
    "order_status", "created_at", "Is Return", "return_amount",
    "FINAL STORE", "NEW_REPEAT",
]


@st.cache_data(show_spinner=False)
def load_orders_csv(path: str) -> pd.DataFrame:
    available = pd.read_csv(path, nrows=0).columns.tolist()
    load_cols = [c for c in COLS_LOAD if c in available]
    df = pd.read_csv(path, usecols=load_cols, low_memory=False)
    df["id"]                     = df["id"].astype(str)
    df["user_id"]                = df["user_id"].astype(str)
    df["contact_person_number"]  = df["contact_person_number"].astype(str)
    df["Is Return"]              = pd.to_numeric(df.get("Is Return", 0), errors="coerce").fillna(0).astype(int)
    df["order_amount"]           = pd.to_numeric(df.get("order_amount", 0), errors="coerce").fillna(0)
    df["return_amount"]          = pd.to_numeric(df.get("return_amount", 0), errors="coerce").fillna(0)
    df["created_at"]             = pd.to_datetime(df["created_at"], errors="coerce")
    return df


@st.cache_data(show_spinner=False)
def build_customer_summary(path: str) -> pd.DataFrame:
    """Aggregate CSV by user_id to produce a customer list."""
    df = load_orders_csv(path)
    grp = df.groupby("user_id").agg(
        phone        =("contact_person_number", "first"),
        total_orders =("id", "count"),
        returns      =("Is Return", "sum"),
        total_spent  =("order_amount", "sum"),
        first_order  =("created_at", "min"),
        last_repeat  =("NEW_REPEAT", "last"),
    ).reset_index()
    grp["first_order"] = grp["first_order"].dt.strftime("%d %b %Y")
    grp["returns"]     = grp["returns"].astype(int)
    return grp.sort_values("total_spent", ascending=False)


# ── Page ──────────────────────────────────────────────────────────────────────

st.markdown("## 👥 Customers")

if not os.path.exists(CSV_PATH):
    st.info("No orders data found. Upload a CSV from the Orders module.")
    st.stop()

search = st.text_input("Search by phone or user ID", placeholder="e.g. 918800803357 or 42")

cust_df = build_customer_summary(CSV_PATH)

if search:
    s = search.strip().lower()
    cust_df = cust_df[
        cust_df["phone"].str.lower().str.contains(s, na=False) |
        cust_df["user_id"].str.lower().str.contains(s, na=False)
    ]

if cust_df.empty:
    st.info("No customers found.")
    st.stop()

st.caption(f"{len(cust_df):,} customer{'s' if len(cust_df) != 1 else ''}")

# ── Table header ──────────────────────────────────────────────────────────────

PAGE_SIZE   = 30
total_pages = max(1, (len(cust_df) - 1) // PAGE_SIZE + 1)
pg_col, _   = st.columns([1, 4])
page        = pg_col.number_input("Page", min_value=1, max_value=total_pages, value=1, step=1, label_visibility="collapsed")
st.caption(f"Page {page} of {total_pages}")
start       = (page - 1) * PAGE_SIZE
page_df     = cust_df.iloc[start : start + PAGE_SIZE]

# Build display table
disp = page_df[[
    "user_id", "phone", "total_orders", "returns", "total_spent", "first_order", "last_repeat"
]].copy()
disp.columns = ["User ID", "Phone", "Orders", "Returns", "Total Spent (₹)", "First Order", "Type"]
disp["Type"] = disp["Type"].apply(lambda x: "🆕 New" if str(x) == "NEW" else ("🔄 Repeat" if str(x) == "REPEAT" else "—"))

if "cust_selected" not in st.session_state:
    st.session_state["cust_selected"] = None

cust_event = st.dataframe(
    disp,
    column_config={
        "Total Spent (₹)": st.column_config.NumberColumn("Total Spent (₹)", format="₹%.0f"),
        "Orders": st.column_config.NumberColumn("Orders", format="%d"),
        "Returns": st.column_config.NumberColumn("Returns", format="%d"),
    },
    selection_mode="single-row",
    on_select="rerun",
    use_container_width=True,
    hide_index=True,
    key=f"cust_df_{page}",
)

sel_rows = cust_event.selection.rows if cust_event.selection.rows else []
if sel_rows:
    new_uid = str(page_df.iloc[sel_rows[0]]["user_id"])
    if new_uid != st.session_state.get("cust_selected"):
        st.session_state["cust_selected"] = new_uid

# Profile panel
if st.session_state.get("cust_selected"):
    uid = st.session_state["cust_selected"]
    row_match = cust_df[cust_df["user_id"] == uid]
    if row_match.empty:
        st.session_state["cust_selected"] = None
    else:
        row = row_match.iloc[0]
        phone = str(row["phone"])

        with st.container(border=True):
            c_close, c_title = st.columns([1, 8])
            with c_close:
                if st.button("✕ Close", key=f"close_cust_{uid}"):
                    st.session_state["cust_selected"] = None
                    st.rerun()
            with c_title:
                st.markdown(f"#### Customer {uid}  ·  {phone}")

            wallet = get_wallet_credits_for_customer(uid, phone)
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Total Orders", int(row["total_orders"]))
            k2.metric("Total Spent", f"₹{row['total_spent']:,.0f}")
            k3.metric("Returns", int(row["returns"]))
            k4.metric("Wallet Credits", f"₹{wallet:,.0f}")

            orders_df = load_orders_csv(CSV_PATH)
            user_orders = orders_df[orders_df["user_id"] == uid]

            invalid = {"", "nan", "NoCouponApplied", "None", "none"}
            coupons = sorted({
                str(c).strip() for c in user_orders["coupon_code"].dropna().unique()
                if str(c).strip() not in invalid
            })

            st.markdown("**Coupons Used**")
            if coupons:
                st.markdown(" ".join(coupon_pill(c) for c in coupons), unsafe_allow_html=True)
            else:
                st.caption("None used")

            st.markdown("")

            ORDER_STATUS_COLOURS_LOCAL = {
                "delivered": "#2e7d32", "cancelled": "#c62828", "canceled": "#c62828",
                "failed": "#991b1b", "undelivered": "#ea580c", "pending": "#f0a500",
            }
            recent_orders = user_orders.sort_values("created_at", ascending=False)

            with st.expander(f"📦 Order History ({len(user_orders)} orders)", expanded=True):
                show_all = st.checkbox("Show all", key=f"show_all_{uid}")
                display_orders = recent_orders if show_all else recent_orders.head(10)
                oh = st.columns([1.2, 1.0, 1.0, 1.1, 1.0, 0.6])
                for col, label in zip(oh, ["Order ID", "Date", "Amount", "Status", "Store", "Return"]):
                    col.markdown(f"**{label}**")
                st.markdown('<hr style="margin:2px 0 6px 0">', unsafe_allow_html=True)
                for _, o in display_orders.iterrows():
                    o_st = str(o.get("order_status", "—"))
                    o_colour = ORDER_STATUS_COLOURS_LOCAL.get(o_st.lower(), "#64748b")
                    or_ = st.columns([1.2, 1.0, 1.0, 1.1, 1.0, 0.6])
                    or_[0].write(str(o["id"]))
                    or_[1].write(fmt_dt(o["created_at"]))
                    or_[2].write(f"₹{o['order_amount']:,.0f}")
                    or_[3].markdown(pill(o_st.replace("_", " ").title(), o_colour), unsafe_allow_html=True)
                    or_[4].write(str(o.get("FINAL STORE", "—")))
                    or_[5].write("↩" if int(o.get("Is Return", 0)) else "—")

            db_returns = get_returns_for_customer(phone)
            crm_calls  = get_crm_calls_for_customer(phone)

            if db_returns:
                with st.expander(f"↩ Returns in CX System ({len(db_returns)})", expanded=False):
                    rh = st.columns([0.7, 1.2, 1.1, 1.0, 1.2, 1.0])
                    for col, label in zip(rh, ["RET-ID", "Order ID", "Status", "Type", "Refund Source", "Date"]):
                        col.markdown(f"**{label}**")
                    st.markdown('<hr style="margin:2px 0 6px 0">', unsafe_allow_html=True)
                    for ret in db_returns:
                        r_st = ret["status"]
                        rr = st.columns([0.7, 1.2, 1.1, 1.0, 1.2, 1.0])
                        rr[0].write(f"RET-{ret['id']:03d}")
                        rr[1].write(ret["order_id"])
                        rr[2].markdown(
                            pill(RETURN_STATUS_LABELS.get(r_st, r_st), RETURN_STATUS_COLOURS.get(r_st, "#444")),
                            unsafe_allow_html=True,
                        )
                        rr[3].write(ret.get("type", "—").title())
                        rr[4].write(ret.get("refund_source") or "—")
                        rr[5].write(fmt_dt(ret.get("created_at", "")))

            if crm_calls:
                with st.expander(f"📞 CRM Calls ({len(crm_calls)})", expanded=False):
                    ch = st.columns([1.4, 1.1, 1.8, 1.2])
                    for col, label in zip(ch, ["Order ID", "Call Status", "Drop-off Reason", "Date"]):
                        col.markdown(f"**{label}**")
                    st.markdown('<hr style="margin:2px 0 6px 0">', unsafe_allow_html=True)
                    DROP_LABELS = {
                        "cx_unavailable": "CX Unavailable", "not_interested": "Not Interested",
                        "price_too_expensive": "Price Too Expensive", "bad_delivery": "Didn't Like Delivery",
                        "forgot_coupon": "Forgot Coupon", "too_slow": "Delivery Too Slow",
                        "product_quality": "Product Quality Issue", "other": "Other",
                    }
                    for call in crm_calls:
                        c_st = call["call_status"]
                        cr = st.columns([1.4, 1.1, 1.8, 1.2])
                        cr[0].write(call["order_id"])
                        cr[1].markdown(pill(c_st.replace("_", " ").title(), CRM_COLOURS.get(c_st, "#444")), unsafe_allow_html=True)
                        cr[2].write(DROP_LABELS.get(call.get("drop_off_reason", ""), call.get("drop_off_reason") or "—"))
                        cr[3].write(fmt_dt(call.get("assigned_at", "")))
