"""
Ozi CX Dashboard — entry point.
Handles: auth gate, global CSS, page config, sidebar, routing.
"""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from db.connection import init_db
from utils.auth import get_current_user, login, logout
from db.queries import get_cx_users, toggle_availability, assign_calls_to_available_agents

st.set_page_config(
    page_title="Ozi CX",
    page_icon="🟣",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()

# ── Auto-seed on first run ────────────────────────────────────────────────────
from db.connection import get_conn as _get_conn
_conn = _get_conn()
_user_count = _conn.execute("SELECT COUNT(*) FROM cx_users").fetchone()[0]
_conn.close()
if _user_count == 0:
    from seed import seed as _seed
    _seed()

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

html, body, [class*="css"], .stMarkdown, button, input, select, textarea, label {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

/* ── Dark sidebar ──────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1e1b4b 0%, #2e1065 100%) !important;
}
section[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,0.12) !important;
}
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] .stMarkdown span,
section[data-testid="stSidebar"] .stMarkdown div,
section[data-testid="stSidebar"] label {
    color: #e2e8f0 !important;
}
[data-testid="stSidebarNavItems"] a {
    border-radius: 8px !important;
    color: #c4b5fd !important;
    font-weight: 500 !important;
    padding: 6px 12px !important;
    margin: 1px 0 !important;
    transition: background 0.15s ease !important;
}
[data-testid="stSidebarNavItems"] a:hover {
    background: rgba(139,92,246,0.2) !important;
    color: #fff !important;
}
[data-testid="stSidebarNavItems"] [aria-current="page"] a,
[data-testid="stSidebarNavItems"] a[aria-current="page"] {
    background: rgba(139,92,246,0.3) !important;
    color: #fff !important;
    font-weight: 600 !important;
}
section[data-testid="stSidebar"] .stButton > button {
    background: rgba(255,255,255,0.08) !important;
    color: #e2e8f0 !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    border-radius: 10px !important;
    font-weight: 500 !important;
    transition: background 0.15s !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,0.16) !important;
}

/* ── Main layout ───────────────────────────────────────── */
.main .block-container {
    padding-top: 1.25rem !important;
    max-width: 1400px !important;
}

/* ── KPI cards ─────────────────────────────────────────── */
.kpi-card {
    background: #fff;
    border: 1px solid #ede9fe;
    border-radius: 14px;
    padding: 20px 22px;
    box-shadow: 0 1px 4px rgba(109,40,217,0.07);
    border-left: 4px solid #6d28d9;
    height: 100%;
}
.kpi-card .kpi-icon  { font-size: 1.5rem; margin-bottom: 6px; }
.kpi-card .kpi-value { font-size: 2rem; font-weight: 800; color: #1e1e2e; line-height: 1.1; }
.kpi-card .kpi-label { font-size: 0.72rem; font-weight: 700; color: #6d28d9;
                        text-transform: uppercase; letter-spacing: 0.08em; margin-top: 6px; }

/* ── Agent queue card ──────────────────────────────────── */
.queue-card {
    background: #fff;
    border: 1px solid #ede9fe;
    border-radius: 12px;
    padding: 12px 16px;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    transition: box-shadow 0.15s;
}
.queue-card:hover { box-shadow: 0 4px 12px rgba(109,40,217,0.12); }

/* ── Tabs ──────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 2px !important;
    background: transparent !important;
    border-bottom: 2px solid #ede9fe !important;
    padding-bottom: 0 !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px 8px 0 0 !important;
    font-weight: 500 !important;
    color: #64748b !important;
    padding: 8px 14px !important;
    font-size: 0.85rem !important;
}
.stTabs [aria-selected="true"] {
    background: #f5f3ff !important;
    color: #6d28d9 !important;
    font-weight: 700 !important;
    border-bottom: 3px solid #6d28d9 !important;
}

/* ── Buttons ───────────────────────────────────────────── */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #6d28d9, #4f46e5) !important;
    border: none !important;
    border-radius: 9px !important;
    font-weight: 600 !important;
    letter-spacing: 0.01em !important;
    box-shadow: 0 2px 8px rgba(109,40,217,0.3) !important;
    transition: box-shadow 0.15s, transform 0.1s !important;
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 6px 16px rgba(109,40,217,0.4) !important;
    transform: translateY(-1px) !important;
}
.stButton > button[kind="secondary"] {
    border: 1.5px solid #6d28d9 !important;
    color: #6d28d9 !important;
    border-radius: 9px !important;
    font-weight: 600 !important;
    background: transparent !important;
}

/* ── Inputs ────────────────────────────────────────────── */
.stTextInput input, .stTextArea textarea, .stNumberInput input, .stDateInput input {
    border-radius: 8px !important;
    border: 1.5px solid #e2e8f0 !important;
    transition: border-color 0.15s, box-shadow 0.15s !important;
}
.stTextInput input:focus, .stTextArea textarea:focus, .stNumberInput input:focus {
    border-color: #6d28d9 !important;
    box-shadow: 0 0 0 3px rgba(109,40,217,0.1) !important;
}
div[data-baseweb="select"] > div {
    border-radius: 8px !important;
    border: 1.5px solid #e2e8f0 !important;
}

/* ── Expander ──────────────────────────────────────────── */
[data-testid="stExpander"] {
    border: 1px solid #ede9fe !important;
    border-radius: 10px !important;
    overflow: hidden !important;
}

/* ── Divider ───────────────────────────────────────────── */
hr { border-color: #ede9fe !important; }

/* ── Alerts ────────────────────────────────────────────── */
[data-testid="stAlert"] { border-radius: 10px !important; }

/* ── Metric default ────────────────────────────────────── */
[data-testid="metric-container"] {
    background: #faf5ff !important;
    border: 1px solid #ede9fe !important;
    border-radius: 12px !important;
    padding: 1rem 1.25rem !important;
}
</style>
""", unsafe_allow_html=True)

# ── Auth gate ─────────────────────────────────────────────────────────────────
user = get_current_user()

if not user:
    st.markdown("""
    <style>section[data-testid="stSidebar"]{display:none}</style>
    """, unsafe_allow_html=True)
    col = st.columns([1, 1.8, 1])[1]
    with col:
        st.markdown("""
        <div style="text-align:center;margin:40px 0 32px">
            <div style="font-size:2.8rem;font-weight:900;color:#6d28d9;letter-spacing:-2px;line-height:1">
                ozi
                <span style="font-size:1rem;font-weight:600;color:#a78bfa;vertical-align:super;letter-spacing:0">CX</span>
            </div>
            <div style="color:#94a3b8;margin-top:6px;font-size:0.9rem;font-weight:500">
                Customer Experience Dashboard
            </div>
        </div>
        """, unsafe_allow_html=True)

        users_raw = get_cx_users(active_only=True)
        _ORDER    = {"admin": 0, "supervisor": 1, "cx_lead": 2, "agent": 3, "wh_user": 4}
        users_sorted = sorted(users_raw, key=lambda u: _ORDER.get(u["role"], 9))
        options = {
            u["id"]: f"{u['name']}  ·  {u['role'].replace('_', ' ').title()}"
            for u in users_sorted
        }
        selected_id = st.selectbox("Who are you?", list(options.keys()), format_func=lambda x: options[x])
        if st.button("Log In →", type="primary", use_container_width=True):
            login(selected_id)
            st.rerun()
    st.stop()

# ── Logged in ─────────────────────────────────────────────────────────────────
role = user["role"]

ROLE_COLOURS = {
    "admin":      "#ef4444",
    "supervisor": "#f97316",
    "cx_lead":    "#8b5cf6",
    "agent":      "#3b82f6",
    "wh_user":    "#10b981",
}

def _initials(name: str) -> str:
    parts = name.strip().split()
    return (parts[0][0] + parts[-1][0]).upper() if len(parts) >= 2 else name[:2].upper()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    # Wordmark
    st.markdown(
        '<div style="font-size:1.6rem;font-weight:900;color:#fff;letter-spacing:-2px;padding:6px 0 22px 4px">'
        'ozi<span style="font-size:0.75rem;font-weight:600;color:#a78bfa;vertical-align:super;letter-spacing:0;margin-left:2px">CX</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    # Avatar + name + role badge
    badge_colour = ROLE_COLOURS.get(role, "#64748b")
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:18px;padding:12px;'
        f'background:rgba(255,255,255,0.06);border-radius:12px;border:1px solid rgba(255,255,255,0.1)">'
        f'  <div style="width:44px;height:44px;border-radius:50%;flex-shrink:0;'
        f'       background:linear-gradient(135deg,#7c3aed,#4f46e5);'
        f'       display:flex;align-items:center;justify-content:center;'
        f'       font-weight:800;color:#fff;font-size:1rem;'
        f'       box-shadow:0 2px 10px rgba(109,40,217,0.5)">'
        f'    {_initials(user["name"])}'
        f'  </div>'
        f'  <div style="overflow:hidden">'
        f'    <div style="font-weight:700;color:#fff;font-size:0.9rem;white-space:nowrap;'
        f'         overflow:hidden;text-overflow:ellipsis">{user["name"]}</div>'
        f'    <span style="background:{badge_colour};color:#fff;padding:2px 9px;'
        f'          border-radius:20px;font-size:0.65rem;font-weight:700;letter-spacing:0.03em">'
        f'      {role.replace("_"," ").title()}</span>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Availability toggle
    avail = bool(user.get("is_available", 0))
    if st.button(
        "🟢  Available" if avail else "⚫  Unavailable",
        key="avail_toggle",
        help="Toggle your availability",
        use_container_width=True,
    ):
        toggle_availability(user["id"], not avail)
        if not avail:
            assign_calls_to_available_agents()
        st.session_state["current_user"] = {**user, "is_available": int(not avail)}
        st.rerun()

# ── Pages ─────────────────────────────────────────────────────────────────────
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

with st.sidebar:
    st.divider()
    if st.button("↩  Log out", use_container_width=True):
        logout()

pg.run()
