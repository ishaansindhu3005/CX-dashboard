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
role_label = role.replace("_", " ").title()

st.markdown(
    f'<h2 style="margin-bottom:4px">👋 Hi, {user.get("name","").split()[0] if user.get("name") else "there"}</h2>'
    f'<p style="color:#64748b;margin-top:0">{role_label} · Ozi CX Dashboard</p>',
    unsafe_allow_html=True,
)
st.divider()

if role in ("admin", "supervisor", "cx_lead"):
    # ── Aggregate view ──────────────────────────────────────────────────────
    stats = get_dashboard_stats_admin()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📦 Open Returns",     stats["open_returns"])
    c2.metric("💰 Open Refunds",     stats["open_refunds"])
    c3.metric("📞 Open CRM Calls",   stats["open_calls"])
    c4.metric("⚠️ Open Short Picks", stats["open_short_picks"])

    st.markdown("### Team Queue")
    team = get_agent_queue_summary()
    if team:
        th = st.columns([2.5, 1.5, 1.2, 1.2, 1.2, 1.2])
        for col, label in zip(th, ["Name", "Role", "Available", "Returns", "Calls", "Short Picks"]):
            col.markdown(f"**{label}**")
        st.markdown('<hr style="margin:4px 0 8px 0">', unsafe_allow_html=True)
        for a in team:
            row = st.columns([2.5, 1.5, 1.2, 1.2, 1.2, 1.2])
            row[0].write(a["name"])
            row[1].write(a["role"].replace("_", " ").title())
            row[2].write("🟢 Yes" if a["is_available"] else "⚫ No")
            row[3].write(str(a["returns"]))
            row[4].write(str(a["calls"]))
            row[5].write(str(a["short_picks"]))
    else:
        st.info("No agents found.")

else:
    # ── Personal queue view ─────────────────────────────────────────────────
    uid   = user.get("id")
    if not uid:
        st.warning("Session expired — please log out and back in.")
        st.stop()

    stats = get_dashboard_stats_agent(uid)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📦 My Pending Returns",    stats["my_returns"])
    c2.metric("💰 My Pending Refunds",    stats["my_refunds"])
    c3.metric("📞 My CRM Calls",          stats["my_calls"])
    c4.metric("⚠️ My Short-Pick Actions", stats["my_short_picks"])

    st.markdown("### Your Queue")

    q_returns     = get_returns_for_agent(uid, "pending_action")
    q_calls       = get_crm_calls_for_agent(uid, limit=5)
    q_short_picks = get_short_picks_for_agent(uid, limit=5)

    col_r, col_c, col_s = st.columns(3)

    with col_r:
        st.markdown("**📦 Pending Returns**")
        if q_returns:
            for r in q_returns:
                st.markdown(
                    f"`{r['order_id']}` — {r['customer_name'] or '—'}  \n"
                    f"<small>₹{r['total_return_value']:,.0f} · {r['type'].title()}</small>",
                    unsafe_allow_html=True,
                )
        else:
            st.success("All clear ✓")

    with col_c:
        st.markdown("**📞 Pending CRM Calls**")
        if q_calls:
            for c in q_calls:
                st.markdown(
                    f"`{c['order_id']}` — {c['customer_name'] or '—'}  \n"
                    f"<small>{c.get('order_status','—')} · {c['call_status'].replace('_',' ').title()}</small>",
                    unsafe_allow_html=True,
                )
        else:
            st.success("All clear ✓")

    with col_s:
        st.markdown("**⚠️ Pending Short Picks**")
        if q_short_picks:
            for sp in q_short_picks:
                st.markdown(
                    f"`{sp['order_id']}` — {sp['customer_name'] or '—'}  \n"
                    f"<small>{sp.get('short_item_count',0)} item(s) · {sp['action_status'].replace('_',' ').title()}</small>",
                    unsafe_allow_html=True,
                )
        else:
            st.success("All clear ✓")
