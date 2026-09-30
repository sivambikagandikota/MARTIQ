"""
MARTIQ - Configuration
-----------------------
Central place for all settings so nothing important is hardcoded
inside individual page files. Change values here, not inside views/.
"""

import os

# ----------------------------------------------------------------
# PATHS
# ----------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_DIR = os.path.join(BASE_DIR, "database")
DATABASE_PATH = os.path.join(DATABASE_DIR, "martiq.db")
DATA_DIR = os.path.join(BASE_DIR, "data")
DATASET_PATH = os.path.join(DATA_DIR, "SuperMarket Analysis.csv")
LOGO_DIR = os.path.join(BASE_DIR, "assets", "logo")

# ----------------------------------------------------------------
# APP INFO
# ----------------------------------------------------------------
APP_NAME = "MARTIQ"
APP_TAGLINE = "Smart Supermarket Management & Intelligence System"

# ----------------------------------------------------------------
# BUSINESS SETTINGS
# ----------------------------------------------------------------
DEFAULT_GST_PERCENT = 5.0          # used as a default when adding a product
CURRENCY_SYMBOL = "₹"

# ----------------------------------------------------------------
# DEMO LOGIN (for presentation / testing only)
# ----------------------------------------------------------------
DEMO_USERNAME = "admin"
DEMO_PASSWORD = "martiq123"

# ----------------------------------------------------------------
# WALK-IN CUSTOMER
# ----------------------------------------------------------------
# bills.customer_id is NOT NULL (see database.py). Rather than
# altering that constraint, Billing uses one seeded placeholder
# customer for walk-in sales (no name/phone/email captured).
WALKIN_CUSTOMER_NAME = "Walk-in Customer"
WALKIN_CUSTOMER_PHONE = "0000000000"

# ----------------------------------------------------------------
# STOCK THRESHOLDS
# ----------------------------------------------------------------
# A product is "Low Stock" when stock <= min_stock_level (and > 0)
# A product is "Out of Stock" when stock == 0

# ----------------------------------------------------------------
# THEME (green supermarket theme)
# ----------------------------------------------------------------
THEME = {
    "primary": "#1E8449",       # deep green
    "primary_light": "#2ECC71", # bright green
    "accent": "#F4D03F",        # warm yellow accent
    "background": "#F8FBF9",    # near-white background
    "card_bg": "#FFFFFF",
    "text_dark": "#1B2A22",
    "text_muted": "#6B7C72",
    "danger": "#E74C3C",
    "warning": "#F39C12",
    "success": "#27AE60",
}

# ----------------------------------------------------------------
# SESSION STATE KEYS (used consistently across all pages)
# ----------------------------------------------------------------
SESSION_LOGGED_IN = "martiq_logged_in"
SESSION_USERNAME = "martiq_username"
SESSION_PAGE = "martiq_current_page"
SESSION_CART = "martiq_cart"

# ----------------------------------------------------------------
# SIDEBAR NAVIGATION
# ----------------------------------------------------------------
# (sidebar label, internal page key)
NAV_ITEMS = [
    ("🏠 Dashboard", "Dashboard"),
    ("👥 Customers", "Customers"),
    ("📦 Products", "Products"),
    ("🧾 Billing", "Billing"),
    ("📊 Analytics", "Analytics"),
    ("📈 Data Analysis", "Data Analysis"),
    ("📑 Reports", "Reports"),
    ("🤖 Smart Inventory", "Inventory"),
]
DEFAULT_PAGE = "Dashboard"
