import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from db.connection import init_db, get_conn
from utils.rbac import has_permission, _load_permissions_from_db

init_db()

from utils.page_utils import get_page_user
role, user = get_page_user()

if not has_permission(role, "roles", "view"):
    st.markdown("## 🔑 Roles & Permissions")
    st.error("🚫 Access Denied — you don't have permission to view this module.")
    st.stop()

st.markdown("## 🔑 Roles & Permissions")

can_edit = has_permission(role, "roles", "edit")

ALL_MODULES = [
    "dashboard", "returns", "refunds", "customers",
    "orders", "crm_calling", "short_picks", "users", "roles",
]
ALL_ACTIONS = ["view", "action", "call", "approve", "reject", "pickup", "reassign", "create", "edit", "delete"]
ALL_ROLES   = ["agent", "cx_lead", "wh_user", "supervisor", "admin"]

conn = get_conn()
rows = conn.execute("SELECT role, module, action FROM role_permissions ORDER BY role, module, action").fetchall()
conn.close()

# Build permission matrix: {role: {(module, action)}}
perms: dict = {}
for r in rows:
    perms.setdefault(r["role"], set()).add((r["module"], r["action"]))

# ── Permission matrix view ────────────────────────────────────────────────────
for role_name in ALL_ROLES:
    role_perms = perms.get(role_name, set())
    with st.expander(f"{role_name.replace('_', ' ').title()} — {len(role_perms)} permissions", expanded=False):
        header = st.columns([2] + [0.8] * len(ALL_ACTIONS))
        header[0].markdown("**Module**")
        for i, a in enumerate(ALL_ACTIONS):
            header[i + 1].markdown(f"**{a}**")

        for mod in ALL_MODULES:
            row = st.columns([2] + [0.8] * len(ALL_ACTIONS))
            row[0].write(mod)
            for i, act in enumerate(ALL_ACTIONS):
                has = (mod, act) in role_perms
                if can_edit:
                    new_val = row[i + 1].checkbox(
                        "", value=has,
                        key=f"perm_{role_name}_{mod}_{act}",
                        label_visibility="collapsed",
                    )
                    if new_val != has:
                        cnn = get_conn()
                        if new_val:
                            cnn.execute(
                                "INSERT OR IGNORE INTO role_permissions (role, module, action) VALUES (?,?,?)",
                                (role_name, mod, act)
                            )
                        else:
                            cnn.execute(
                                "DELETE FROM role_permissions WHERE role=? AND module=? AND action=?",
                                (role_name, mod, act)
                            )
                        cnn.commit()
                        cnn.close()
                        # Bust the RBAC cache
                        _load_permissions_from_db.clear()
                        st.rerun()
                else:
                    row[i + 1].write("✓" if has else "·")
