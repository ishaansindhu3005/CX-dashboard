import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from db.queries import (
    get_dashboard_stats_admin, get_dashboard_stats_agent,
    get_agent_queue_summary, get_returns_for_agent,
    get_crm_calls_for_agent, get_short_picks_for_agent,
)
from utils.page_utils import get_page_user

role, user = get_page_user()
first_name = user.get("name", "").split()[0] if user.get("name") else "there"

# ── KPI card helper ───────────────────────────────────────────────────────────

def kpi(icon, label, value, colour="#6d28d9"):
    st.markdown(
        f'<div class="kpi-card" style="border-left-color:{colour}">'
        f'  <div class="kpi-icon">{icon}</div>'
        f'  <div class="kpi-value">{value}</div>'
        f'  <div class="kpi-label" style="color:{colour}">{label}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

# ── Page header ───────────────────────────────────────────────────────────────
st.markdown(
    f'<h2 style="margin-bottom:2px;font-weight:800">👋 Hi, {first_name}</h2>'
    f'<p style="color:#94a3b8;margin-top:0;font-size:0.9rem">'
    f'{role.replace("_"," ").title()} · Ozi CX Dashboard</p>',
    unsafe_allow_html=True,
)
st.markdown('<div style="margin-bottom:8px"></div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# ADMIN / SUPERVISOR / CX_LEAD VIEW
# ══════════════════════════════════════════════════════════════════════════════
if role in ("admin", "supervisor", "cx_lead"):
    stats = get_dashboard_stats_admin()

    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi("📦", "Open Returns",     stats["open_returns"],     "#6d28d9")
    with c2: kpi("💰", "Open Refunds",     stats["open_refunds"],     "#0284c7")
    with c3: kpi("📞", "Open CRM Calls",   stats["open_calls"],       "#f0a500")
    with c4: kpi("⚠️", "Open Short Picks", stats["open_short_picks"], "#dc2626")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 👥 Team Queue")

    ROLE_COLOURS = {
        "admin": "#ef4444", "supervisor": "#f97316",
        "cx_lead": "#8b5cf6", "agent": "#3b82f6", "wh_user": "#10b981",
    }

    team = get_agent_queue_summary()
    if team:
        # Header
        hcols = st.columns([2.2, 1.3, 1, 0.9, 0.9, 0.9])
        for col, lbl in zip(hcols, ["Agent", "Role", "Status", "Returns", "Calls", "Short Picks"]):
            col.markdown(f"<small><b style='color:#94a3b8;text-transform:uppercase;letter-spacing:.06em'>{lbl}</b></small>", unsafe_allow_html=True)
        st.markdown('<hr style="margin:4px 0 8px 0;border-color:#ede9fe">', unsafe_allow_html=True)

        for a in team:
            rc = ROLE_COLOURS.get(a["role"], "#64748b")
            avail_html = (
                '<span style="background:#16a34a;color:#fff;padding:2px 8px;border-radius:20px;font-size:0.7rem;font-weight:600">● Online</span>'
                if a["is_available"] else
                '<span style="background:#374151;color:#9ca3af;padding:2px 8px;border-radius:20px;font-size:0.7rem;font-weight:600">○ Offline</span>'
            )
            row = st.columns([2.2, 1.3, 1, 0.9, 0.9, 0.9])
            row[0].markdown(f"**{a['name']}**")
            row[1].markdown(
                f'<span style="background:{rc}22;color:{rc};padding:2px 8px;border-radius:20px;'
                f'font-size:0.7rem;font-weight:700">{a["role"].replace("_"," ").title()}</span>',
                unsafe_allow_html=True,
            )
            row[2].markdown(avail_html, unsafe_allow_html=True)
            row[3].write(str(a["returns"]))
            row[4].write(str(a["calls"]))
            row[5].write(str(a["short_picks"]))
    else:
        st.info("No agents found.")

# ══════════════════════════════════════════════════════════════════════════════
# AGENT VIEW — clickable queue items
# ══════════════════════════════════════════════════════════════════════════════
else:
    uid = user.get("id")
    if not uid:
        st.warning("Session expired — please log out and back in.")
        st.stop()

    stats = get_dashboard_stats_agent(uid)

    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi("📦", "My Pending Returns",    stats["my_returns"],     "#6d28d9")
    with c2: kpi("💰", "My Pending Refunds",    stats["my_refunds"],     "#0284c7")
    with c3: kpi("📞", "My CRM Calls",          stats["my_calls"],       "#f0a500")
    with c4: kpi("⚠️", "My Short-Pick Actions", stats["my_short_picks"], "#dc2626")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 📋 Your Queue")

    q_returns     = get_returns_for_agent(uid, "pending_action")
    q_calls       = get_crm_calls_for_agent(uid, limit=5)
    q_short_picks = get_short_picks_for_agent(uid, limit=5)

    col_r, col_c, col_s = st.columns(3)

    # ── Pending Returns ───────────────────────────────────────────────────────
    with col_r:
        st.markdown(
            '<div style="font-weight:700;font-size:0.95rem;margin-bottom:10px;color:#6d28d9">📦 Pending Returns</div>',
            unsafe_allow_html=True,
        )
        if q_returns:
            for r in q_returns:
                item_col, btn_col = st.columns([5, 1.2])
                with item_col:
                    st.markdown(
                        f'<div style="background:#faf5ff;border:1px solid #ede9fe;border-radius:10px;'
                        f'padding:10px 12px;margin-bottom:4px">'
                        f'  <div style="font-weight:600;font-size:0.85rem">{r["order_id"]}</div>'
                        f'  <div style="color:#64748b;font-size:0.75rem">'
                        f'    {r.get("customer_name") or "—"} · ₹{r["total_return_value"]:,.0f}'
                        f'  </div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                with btn_col:
                    if st.button("Open", key=f"dash_ret_{r['id']}", type="primary"):
                        st.session_state["selected_pending_action"] = r["id"]
                        st.switch_page("pages/1_Returns.py")
        else:
            st.markdown(
                '<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;'
                'padding:12px;color:#16a34a;font-weight:600;font-size:0.85rem;text-align:center">'
                '✓ All clear'
                '</div>',
                unsafe_allow_html=True,
            )

    # ── Pending CRM Calls ─────────────────────────────────────────────────────
    with col_c:
        st.markdown(
            '<div style="font-weight:700;font-size:0.95rem;margin-bottom:10px;color:#f0a500">📞 Pending CRM Calls</div>',
            unsafe_allow_html=True,
        )
        if q_calls:
            for c in q_calls:
                item_col, btn_col = st.columns([5, 1.2])
                with item_col:
                    st.markdown(
                        f'<div style="background:#fffbeb;border:1px solid #fde68a;border-radius:10px;'
                        f'padding:10px 12px;margin-bottom:4px">'
                        f'  <div style="font-weight:600;font-size:0.85rem">{c["order_id"]}</div>'
                        f'  <div style="color:#64748b;font-size:0.75rem">'
                        f'    {c.get("customer_name") or "—"} · {c.get("order_status","—")}'
                        f'  </div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                with btn_col:
                    if st.button("Open", key=f"dash_crm_{c['id']}", type="primary"):
                        st.session_state["selected_pending"] = c["id"]
                        st.switch_page("pages/7_CRM_Calling.py")
        else:
            st.markdown(
                '<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;'
                'padding:12px;color:#16a34a;font-weight:600;font-size:0.85rem;text-align:center">'
                '✓ All clear'
                '</div>',
                unsafe_allow_html=True,
            )

    # ── Pending Short Picks ───────────────────────────────────────────────────
    with col_s:
        st.markdown(
            '<div style="font-weight:700;font-size:0.95rem;margin-bottom:10px;color:#dc2626">⚠️ Pending Short Picks</div>',
            unsafe_allow_html=True,
        )
        if q_short_picks:
            for sp in q_short_picks:
                item_col, btn_col = st.columns([5, 1.2])
                with item_col:
                    st.markdown(
                        f'<div style="background:#fff1f2;border:1px solid #fecdd3;border-radius:10px;'
                        f'padding:10px 12px;margin-bottom:4px">'
                        f'  <div style="font-weight:600;font-size:0.85rem">{sp["order_id"]}</div>'
                        f'  <div style="color:#64748b;font-size:0.75rem">'
                        f'    {sp.get("customer_name") or "—"} · {sp.get("short_item_count",0)} item(s)'
                        f'  </div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                with btn_col:
                    if st.button("Open", key=f"dash_sp_{sp['id']}", type="primary"):
                        st.session_state["selected_pending"] = sp["id"]
                        st.switch_page("pages/8_Short_Picks.py")
        else:
            st.markdown(
                '<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;'
                'padding:12px;color:#16a34a;font-weight:600;font-size:0.85rem;text-align:center">'
                '✓ All clear'
                '</div>',
                unsafe_allow_html=True,
            )
