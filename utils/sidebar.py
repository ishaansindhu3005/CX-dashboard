"""
Centralised sidebar renderer.

Usage in every page:
    from utils.sidebar import render_sidebar
    role, user = render_sidebar()

Returns (role: str, user: dict).
Redirects to app.py (login screen) if not authenticated.
ALL navigation links are always shown — individual pages handle access denied.
"""
import streamlit as st
from utils.auth import require_login, logout
from db.queries import toggle_availability, assign_calls_to_available_agents

# ── All modules in display order — always shown regardless of role ─────────────

_MODULE_PAGES = [
    ("dashboard",   "app.py",                  "🏠 Dashboard"),
    ("returns",     "pages/1_Returns.py",       "📦 Returns"),
    ("refunds",     "pages/2_Refunds.py",       "💰 Refunds"),
    ("customers",   "pages/3_Customers.py",     "👥 Customers"),
    ("orders",      "pages/4_Orders.py",        "📋 Orders"),
    ("crm_calling", "pages/7_CRM_Calling.py",   "📞 CRM Calling"),
    ("short_picks", "pages/8_Short_Picks.py",   "⚠️ Short Picks"),
    ("users",       "pages/5_Users.py",         "👤 Users"),
    ("roles",       "pages/6_Roles.py",         "🔑 Roles"),
]


def render_sidebar() -> tuple:
    """Render the sidebar and return (role, current_user)."""
    user = require_login()
    role: str = user["role"]

    with st.sidebar:
        st.markdown("## 🟣 Ozi CX")
        st.divider()

        # ── Identity + availability ──────────────────────────────────────────
        avail       = bool(user.get("is_available", 0))
        avail_label = "🟢 Available" if avail else "⚫ Unavailable"

        st.markdown(
            f'<div style="font-weight:700;font-size:1rem">{user["name"]}</div>'
            f'<div style="font-size:0.78rem;color:#64748b;margin-bottom:6px">'
            f'{role.replace("_", " ").title()}</div>',
            unsafe_allow_html=True,
        )
        if st.button(
            avail_label,
            key="avail_toggle",
            help="Toggle your availability for call assignment",
            use_container_width=True,
        ):
            new_avail = not avail
            toggle_availability(user["id"], new_avail)
            if new_avail:
                assign_calls_to_available_agents()
            st.session_state["current_user"] = {**user, "is_available": int(new_avail)}
            st.rerun()

        st.divider()

        # ── Navigation — ALL modules always visible ──────────────────────────
        st.caption("Navigate")
        for _module, path, label in _MODULE_PAGES:
            st.page_link(path, label=label)

        st.divider()

        # ── Log out ──────────────────────────────────────────────────────────
        if st.button("↩ Log out", use_container_width=True):
            logout()

    return role, user
