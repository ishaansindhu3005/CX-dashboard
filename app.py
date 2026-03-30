"""
Ozi CX Dashboard — entry point.

In Streamlit 1.36+ (st.navigation model), this file runs on EVERY page load.
It handles: auth gate, page config, custom sidebar content, and page routing.
Individual page files contain only their own content (no set_page_config/sidebar).
"""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from db.connection import init_db
from utils.auth import get_current_user, login, logout
from db.queries import get_cx_users, toggle_availability, assign_calls_to_available_agents

st.set_page_config(
    page_title="Ozi CX Dashboard",
    page_icon="🟣",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()

# ── Auto-seed on first run (needed for Streamlit Cloud ephemeral DB) ──────────
from db.connection import get_conn as _get_conn
_conn = _get_conn()
_user_count = _conn.execute("SELECT COUNT(*) FROM cx_users").fetchone()[0]
_conn.close()
if _user_count == 0:
    from seed import seed as _seed
    _seed()

# ── Auth gate ─────────────────────────────────────────────────────────────────

user = get_current_user()

if not user:
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] {display: none;}
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("")
    col = st.columns([1, 2, 1])[1]
    with col:
        st.markdown(
            '<div style="text-align:center;font-size:2rem;font-weight:800;color:#6d28d9">🟣 Ozi CX</div>'
            '<div style="text-align:center;color:#64748b;margin-bottom:24px">Customer Experience Dashboard</div>',
            unsafe_allow_html=True,
        )
        users_raw = get_cx_users(active_only=True)
        _ORDER = {"admin": 0, "supervisor": 1, "cx_lead": 2, "agent": 3, "wh_user": 4}
        users_sorted = sorted(users_raw, key=lambda u: _ORDER.get(u["role"], 9))
        options = {
            u["id"]: f"{u['name']}  ·  {u['role'].replace('_', ' ').title()}"
            for u in users_sorted
        }
        selected_id = st.selectbox(
            "Who are you?",
            list(options.keys()),
            format_func=lambda x: options[x],
        )
        if st.button("→  Log In", type="primary", use_container_width=True):
            login(selected_id)
            st.rerun()
    st.stop()

# ── Logged in ─────────────────────────────────────────────────────────────────

role = user["role"]

# ── Custom sidebar top (identity + availability) ───────────────────────────────
with st.sidebar:
    st.markdown(
        f'<div style="font-weight:700;font-size:1rem">{user["name"]}</div>'
        f'<div style="font-size:0.78rem;color:#64748b;margin-bottom:6px">'
        f'{role.replace("_", " ").title()}</div>',
        unsafe_allow_html=True,
    )
    avail = bool(user.get("is_available", 0))
    if st.button(
        "🟢 Available" if avail else "⚫ Unavailable",
        key="avail_toggle",
        help="Toggle your availability for call assignment",
        use_container_width=True,
    ):
        toggle_availability(user["id"], not avail)
        if not avail:
            assign_calls_to_available_agents()
        st.session_state["current_user"] = {**user, "is_available": int(not avail)}
        st.rerun()

# ── Define all pages (always all visible — pages handle their own access denied) ──
pages = [
    st.Page("pages/0_Dashboard.py",   title="Dashboard",   icon="🏠"),
    st.Page("pages/4_Orders.py",      title="Orders",      icon="📋"),
    st.Page("pages/3_Customers.py",   title="Customers",   icon="👥"),
    st.Page("pages/1_Returns.py",     title="Returns",     icon="📦"),
    st.Page("pages/2_Refunds.py",     title="Refunds",     icon="💰"),
    st.Page("pages/7_CRM_Calling.py", title="CRM Calling", icon="📞"),
    st.Page("pages/8_Short_Picks.py", title="Short Picks", icon="⚠️"),
    st.Page("pages/5_Users.py",       title="Users",       icon="👤"),
    st.Page("pages/6_Roles.py",       title="Roles",       icon="🔑"),
]

pg = st.navigation(pages)

# ── Log out at bottom of sidebar ──────────────────────────────────────────────
with st.sidebar:
    st.divider()
    if st.button("↩ Log out", use_container_width=True):
        logout()

pg.run()
