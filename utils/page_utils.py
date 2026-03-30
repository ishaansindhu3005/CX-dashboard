"""
Thin helper for page files — gets the current user and role from session_state.
Auth gating is handled centrally by app.py (which runs on every page load).
"""
import streamlit as st


def get_page_user() -> tuple:
    """
    Return (role: str, user: dict) from session state.
    If not logged in, returns ("agent", {}) — app.py should have already
    handled the auth gate before any page runs.
    """
    user = st.session_state.get("current_user") or {}
    role = user.get("role", "agent")
    return role, user
