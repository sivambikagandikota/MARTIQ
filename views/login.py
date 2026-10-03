"""
MARTIQ - Login Page
---------------------
Renders the login form and validates credentials against the
existing `users` table (created in Phase 1). On success it sets
session state and the app.py router takes over from there.
"""

import streamlit as st
import config
import database
from utils import ui


def render():
    ui.page_header(
        "🔐",
        f"Welcome to {config.APP_NAME}",
        config.APP_TAGLINE,
    )

    left, center, right = st.columns([1, 1.3, 1])

    with center:
        st.markdown('<div class="martiq-card">', unsafe_allow_html=True)

        st.markdown("#### Sign in to continue")

        username = st.text_input("Username", placeholder="Enter your username", key="login_username")
        password = st.text_input("Password", type="password", placeholder="Enter your password", key="login_password")

        login_clicked = st.button("Login", use_container_width=True)

        if login_clicked:
            _handle_login(username, password)

        st.markdown("</div>", unsafe_allow_html=True)

        st.caption(f"Demo account — username: `{config.DEMO_USERNAME}` · password: `{config.DEMO_PASSWORD}`")


def _handle_login(username: str, password: str):
    """Validate input, check credentials, and start the session on success."""
    username = (username or "").strip()
    password = password or ""

    # -------- empty field validation --------
    if not username or not password:
        st.error("Please enter both a username and a password.")
        return

    # -------- credential check against the users table --------
    try:
        is_valid = database.verify_user(username, password)
    except Exception:
        st.error("Something went wrong while checking your credentials. Please try again.")
        return

    if is_valid:
        st.session_state[config.SESSION_LOGGED_IN] = True
        st.session_state[config.SESSION_USERNAME] = username
        st.session_state[config.SESSION_PAGE] = config.DEFAULT_PAGE
        st.success("Login successful. Redirecting to your dashboard...")
        st.rerun()
    else:
        st.error("Invalid username or password. Please try again.")
