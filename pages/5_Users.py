import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from db.connection import init_db, get_conn
from utils.rbac import has_permission

init_db()

from utils.page_utils import get_page_user
role, user = get_page_user()

# ── Access gate — visible to all, write-blocked for non-admin ─────────────────
if not has_permission(role, "users", "view"):
    st.markdown("## 👤 Users")
    st.error("🚫 Access Denied — you don't have permission to view this module.")
    st.stop()

# ── Page ──────────────────────────────────────────────────────────────────────
st.markdown("## 👤 Users")

can_create = has_permission(role, "users", "create")
can_edit   = has_permission(role, "users", "edit")
can_delete = has_permission(role, "users", "delete")

conn = get_conn()
users = conn.execute("SELECT * FROM cx_users ORDER BY name").fetchall()
conn.close()

# ── Top bar ───────────────────────────────────────────────────────────────────
top_left, top_right = st.columns([5, 1])
top_left.markdown(f"**{len(users)} users** in the system")
if can_create and top_right.button("＋ Create User", type="primary"):
    st.session_state["creating_user"] = True

# ── Create user form ──────────────────────────────────────────────────────────
if st.session_state.get("creating_user") and can_create:
    with st.expander("New User", expanded=True):
        with st.form("create_user_form"):
            c1, c2 = st.columns(2)
            new_name  = c1.text_input("Full name *")
            new_email = c2.text_input("Email")
            c3, c4 = st.columns(2)
            new_phone = c3.text_input("Phone")
            new_role  = c4.selectbox("Role *", ["agent", "cx_lead", "wh_user", "supervisor", "admin"],
                                     format_func=lambda r: r.replace("_", " ").title())
            sub, cancel = st.columns(2)
            if sub.form_submit_button("Create", type="primary"):
                if not new_name.strip():
                    st.error("Name is required.")
                else:
                    cnn = get_conn()
                    cnn.execute(
                        "INSERT INTO cx_users (name, email, phone, role, is_active, is_available) VALUES (?,?,?,?,1,0)",
                        (new_name.strip(), new_email.strip() or None, new_phone.strip() or None, new_role)
                    )
                    cnn.commit()
                    cnn.close()
                    st.success(f"User '{new_name}' created.")
                    st.session_state["creating_user"] = False
                    st.rerun()
            if cancel.form_submit_button("Cancel"):
                st.session_state["creating_user"] = False
                st.rerun()

# ── User cards ────────────────────────────────────────────────────────────────
ROLE_ICONS = {
    "agent":      "👤",
    "cx_lead":    "🔑",
    "wh_user":    "🏭",
    "supervisor": "👁",
    "admin":      "⚙️",
}

for u in users:
    with st.container(border=True):
        c1, c2, c3, c4, c5 = st.columns([2.5, 2, 1.5, 1, 1])
        c1.markdown(
            f"**{ROLE_ICONS.get(u['role'], '👤')} {u['name']}**  \n"
            f"<small style='color:#64748b'>{u['email'] or '—'}</small>",
            unsafe_allow_html=True,
        )
        c2.markdown(
            f"<small>{u['phone'] or '—'}</small>",
            unsafe_allow_html=True,
        )
        c3.markdown(
            f"<small>{u['role'].replace('_',' ').title()}</small>",
            unsafe_allow_html=True,
        )
        c4.write("🟢" if u["is_available"] else "⚫")

        if can_edit or can_delete:
            edit_key   = f"edit_user_{u['id']}"
            delete_key = f"del_user_{u['id']}"
            btn_e, btn_d = c5.columns(2)
            if can_edit and btn_e.button("✏️", key=edit_key, help="Edit"):
                st.session_state[f"editing_{u['id']}"] = True
            if can_delete and btn_d.button("🗑", key=delete_key, help="Delete"):
                if u["id"] != user["id"]:  # can't delete yourself
                    cnn = get_conn()
                    cnn.execute("UPDATE cx_users SET is_active=0 WHERE id=?", (u["id"],))
                    cnn.commit()
                    cnn.close()
                    st.warning(f"'{u['name']}' deactivated.")
                    st.rerun()
                else:
                    st.error("You can't deactivate your own account.")

        # ── Inline edit form ──────────────────────────────────────────────────
        if st.session_state.get(f"editing_{u['id']}") and can_edit:
            with st.form(f"edit_form_{u['id']}"):
                ec1, ec2 = st.columns(2)
                upd_name  = ec1.text_input("Name",  value=u["name"])
                upd_email = ec2.text_input("Email", value=u["email"] or "")
                ec3, ec4 = st.columns(2)
                upd_phone = ec3.text_input("Phone", value=u["phone"] or "")
                role_opts = ["agent", "cx_lead", "wh_user", "supervisor", "admin"]
                upd_role  = ec4.selectbox(
                    "Role",
                    role_opts,
                    index=role_opts.index(u["role"]) if u["role"] in role_opts else 0,
                    format_func=lambda r: r.replace("_", " ").title(),
                )
                sv, cn = st.columns(2)
                if sv.form_submit_button("Save", type="primary"):
                    cnn = get_conn()
                    cnn.execute(
                        "UPDATE cx_users SET name=?, email=?, phone=?, role=? WHERE id=?",
                        (upd_name.strip(), upd_email.strip() or None,
                         upd_phone.strip() or None, upd_role, u["id"])
                    )
                    cnn.commit()
                    cnn.close()
                    st.success("Updated.")
                    st.session_state[f"editing_{u['id']}"] = False
                    st.rerun()
                if cn.form_submit_button("Cancel"):
                    st.session_state[f"editing_{u['id']}"] = False
                    st.rerun()
