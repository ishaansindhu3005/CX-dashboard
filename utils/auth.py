"""
Auth helpers.  All functions use st.session_state["current_user"] to track identity.

Login is identity-based (no password) — internal tool only.
"""
import streamlit as st
from db.connection import get_conn


def get_current_user() -> "dict | None":
    """Return the logged-in cx_user dict, or None if not logged in."""
    return st.session_state.get("current_user")


def login(cx_user_id: int) -> None:
    """Set the session to the chosen cx_user."""
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM cx_users WHERE id = ? AND is_active = 1",
        (cx_user_id,)
    ).fetchone()
    conn.close()
    if row:
        st.session_state["current_user"] = dict(row)


def logout() -> None:
    """Clear the session and redirect to the login page."""
    st.session_state.pop("current_user", None)
    st.rerun()


def require_login() -> dict:
    """
    Call at the top of every page.
    If no session exists, redirect to app.py (login screen).
    Returns the current_user dict.
    """
    user = get_current_user()
    if not user:
        st.switch_page("app.py")
        st.stop()
    return user


def refresh_user() -> None:
    """Re-read the current user from DB (picks up is_available changes)."""
    user = get_current_user()
    if not user:
        return
    conn = get_conn()
    row = conn.execute("SELECT * FROM cx_users WHERE id = ?", (user["id"],)).fetchone()
    conn.close()
    if row:
        st.session_state["current_user"] = dict(row)
