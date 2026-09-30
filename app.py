"""
MARTIQ - Main Application Entry Point
---------------------------------------
PHASE 2 VERSION.

app.py is now the router:
  1. Initialize the database (safe to call every run, from Phase 1)
  2. If nobody is logged in -> show the login page and stop
  3. If logged in -> render the sidebar navigation and dispatch to
     whichever page is currently selected in session state

Each page module in views/ only exposes a render() function and
knows nothing about routing - that keeps things simple and avoids
circular imports (views/*.py never import app.py).

NOTE: this folder is named "views" (not "pages") on purpose.
Streamlit auto-generates its own multipage navigation for any
folder literally named "pages" sitting next to app.py, which would
duplicate/conflict with MARTIQ's custom sidebar below.
"""

import streamlit as st

import config
import database
from utils import ui

from views import (
    login,
    dashboard,
    customers,
    products,
    billing,
    analytics,
    reports,
    inventory_intelligence,
    data_analysis,
)

# ------------------------------------------------------------------
# PAGE CONFIG (must be the first Streamlit command)
# ------------------------------------------------------------------
st.set_page_config(
    page_title=config.APP_NAME,
    page_icon="🛒",
    layout="wide",
)

# ------------------------------------------------------------------
# INITIALIZE DATABASE
# ------------------------------------------------------------------
database.init_db()

# ------------------------------------------------------------------
# GLOBAL THEME
# ------------------------------------------------------------------
ui.apply_global_css()

# ------------------------------------------------------------------
# SESSION STATE DEFAULTS
# ------------------------------------------------------------------
if config.SESSION_LOGGED_IN not in st.session_state:
    st.session_state[config.SESSION_LOGGED_IN] = False
if config.SESSION_PAGE not in st.session_state:
    st.session_state[config.SESSION_PAGE] = config.DEFAULT_PAGE

# ------------------------------------------------------------------
# ROUTE MAP: internal page key -> render function
# ------------------------------------------------------------------
PAGE_RENDERERS = {
    "Dashboard": dashboard.render,
    "Customers": customers.render,
    "Products": products.render,
    "Billing": billing.render,
    "Analytics": analytics.render,
    "Reports": reports.render,
    "Inventory": inventory_intelligence.render,
    "Data Analysis": data_analysis.render,
}


def render_sidebar():
    """Render the sidebar navigation, system status, and logout button."""
    with st.sidebar:
        st.markdown(f"### 🛒 {config.APP_NAME}")
        st.caption(config.APP_TAGLINE)
        st.markdown('<span class="martiq-online-pill">🟢 System Online</span>', unsafe_allow_html=True)

        st.markdown("---")

        labels = [label for label, _ in config.NAV_ITEMS]
        keys = [key for _, key in config.NAV_ITEMS]
        current_key = st.session_state[config.SESSION_PAGE]
        current_index = keys.index(current_key) if current_key in keys else 0

        selected_label = st.radio(
            "Navigation",
            labels,
            index=current_index,
            label_visibility="collapsed",
        )
        selected_key = dict(config.NAV_ITEMS)[selected_label]
        st.session_state[config.SESSION_PAGE] = selected_key

        st.markdown("---")
        st.caption(f"Logged in as **{st.session_state.get(config.SESSION_USERNAME, 'Admin')}**")

        if st.button("🚪 Logout", use_container_width=True):
            _logout()


def _logout():
    """Clear the login session and send the user back to the login page."""
    for key in (
        config.SESSION_LOGGED_IN,
        config.SESSION_USERNAME,
        config.SESSION_PAGE,
        config.SESSION_CART,
    ):
        st.session_state.pop(key, None)
    st.rerun()


# ------------------------------------------------------------------
# MAIN ROUTING LOGIC
# ------------------------------------------------------------------
if not st.session_state[config.SESSION_LOGGED_IN]:
    login.render()
    st.stop()

render_sidebar()

current_page_key = st.session_state[config.SESSION_PAGE]
render_function = PAGE_RENDERERS.get(current_page_key, dashboard.render)
render_function()
