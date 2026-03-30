"""
Role-Based Access Control helpers.

Permissions are stored in the `role_permissions` table (seeded by seed.py).
This module provides the two key helpers used everywhere:
  - has_permission(role, module, action) → bool
  - get_accessible_modules(role) → list[str]
"""
import streamlit as st
from db.connection import get_conn


# ── Fallback permission defaults (used if DB is empty / before seeding) ──────

_DEFAULTS: dict[str, list[tuple[str, str]]] = {
    "agent": [
        ("dashboard",    "view"),
        ("returns",      "view"), ("returns",      "action"), ("returns", "create"),
        ("refunds",      "view"),
        ("customers",    "view"),
        ("orders",       "view"),
        ("crm_calling",  "view"), ("crm_calling",  "call"),
        ("short_picks",  "view"), ("short_picks",  "action"),
    ],
    "cx_lead": [
        ("dashboard",    "view"),
        ("returns",      "view"), ("returns",      "action"), ("returns", "approve"), ("returns", "reject"), ("returns", "create"),
        ("refunds",      "view"), ("refunds",      "action"), ("refunds", "approve"), ("refunds", "create"),
        ("customers",    "view"),
        ("orders",       "view"),
        ("crm_calling",  "view"), ("crm_calling",  "call"),
        ("short_picks",  "view"), ("short_picks",  "action"),
    ],
    "wh_user": [
        ("returns",      "view"), ("returns",      "pickup"),
        ("refunds",      "view"),
        ("short_picks",  "view"),
        ("crm_calling",  "view"),
    ],
    "supervisor": [
        ("dashboard",    "view"),
        ("returns",      "view"), ("returns",      "action"), ("returns", "approve"), ("returns", "reject"), ("returns", "create"),
        ("refunds",      "view"), ("refunds",      "action"), ("refunds", "approve"), ("refunds", "create"),
        ("customers",    "view"),
        ("orders",       "view"),
        ("crm_calling",  "view"), ("crm_calling",  "call"),   ("crm_calling",  "reassign"),
        ("short_picks",  "view"), ("short_picks",  "action"), ("short_picks",  "reassign"),
        ("users",        "view"),
    ],
    "admin": [
        ("dashboard",    "view"),
        ("returns",      "view"), ("returns",      "action"), ("returns", "approve"), ("returns", "reject"), ("returns", "create"),
        ("refunds",      "view"), ("refunds",      "action"), ("refunds", "approve"), ("refunds", "create"),
        ("customers",    "view"),
        ("orders",       "view"),
        ("crm_calling",  "view"), ("crm_calling",  "call"),   ("crm_calling",  "reassign"),
        ("short_picks",  "view"), ("short_picks",  "action"), ("short_picks",  "reassign"),
        ("users",        "view"), ("users",        "create"), ("users",        "edit"), ("users",        "delete"),
        ("roles",        "view"), ("roles",        "create"), ("roles",        "edit"), ("roles",        "delete"),
    ],
}

# Module display order for sidebar nav
MODULE_ORDER = [
    "dashboard", "returns", "refunds", "customers",
    "orders", "crm_calling", "short_picks", "users", "roles",
]


@st.cache_data(ttl=60, show_spinner=False)
def _load_permissions_from_db() -> dict[str, set[tuple[str, str]]]:
    """Load all role_permissions into memory. Cached for 60 s."""
    conn = get_conn()
    rows = conn.execute("SELECT role, module, action FROM role_permissions").fetchall()
    conn.close()
    result: dict[str, set[tuple[str, str]]] = {}
    for r in rows:
        result.setdefault(r["role"], set()).add((r["module"], r["action"]))
    return result


def _get_permissions(role: str) -> set[tuple[str, str]]:
    """Return the set of (module, action) pairs allowed for this role."""
    try:
        db_perms = _load_permissions_from_db()
        if db_perms:
            return db_perms.get(role, set())
    except Exception:
        pass
    # Fallback to hardcoded defaults
    return set(_DEFAULTS.get(role, []))


def has_permission(role: str, module: str, action: str) -> bool:
    """Return True if `role` is allowed to perform `action` on `module`."""
    if role == "admin":
        return True
    return (module, action) in _get_permissions(role)


def get_accessible_modules(role: str) -> list[str]:
    """Return ordered list of module names the role can view."""
    perms = _get_permissions(role)
    viewable = {m for m, a in perms if a == "view"}
    return [m for m in MODULE_ORDER if m in viewable]
