"""
MARTIQ - Reports Page
-------------------------
Five downloadable reports (Sales, Billing, Product, Inventory,
Customer), each backed by a real database.py query and exportable
as CSV or Excel. All filters are optional; an empty result shows a
friendly message instead of an empty table.
"""

from datetime import date, timedelta

import pandas as pd
import streamlit as st

import config
import database
from utils import helpers, ui


def render():
    ui.page_header("📑", "Reports", "Generate and export detailed business reports")

    tab_sales, tab_billing, tab_product, tab_inventory, tab_customer = st.tabs(
        ["💰 Sales Report", "🧾 Billing Report", "📦 Product Report", "📊 Inventory Report", "👥 Customer Report"]
    )
    with tab_sales:
        _render_sales_report()
    with tab_billing:
        _render_billing_report()
    with tab_product:
        _render_product_report()
    with tab_inventory:
        _render_inventory_report()
    with tab_customer:
        _render_customer_report()


def _date_range_inputs(key_prefix: str):
    col1, col2 = st.columns(2)
    with col1:
        start = st.date_input("From", value=date.today() - timedelta(days=30), key=f"{key_prefix}_start")
    with col2:
        end = st.date_input("To", value=date.today(), key=f"{key_prefix}_end")
    return start.isoformat(), end.isoformat()


def _download_buttons(df: pd.DataFrame, filename_base: str, key_prefix: str):
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "📥 Download CSV", data=helpers.df_to_csv_bytes(df),
            file_name=f"{filename_base}.csv", mime="text/csv",
            use_container_width=True, key=f"{key_prefix}_csv",
        )
    with col2:
        st.download_button(
            "📥 Download Excel", data=helpers.df_to_excel_bytes(df, filename_base),
            file_name=f"{filename_base}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True, key=f"{key_prefix}_xlsx",
        )


# ----------------------------------------------------------------
# SALES REPORT
# ----------------------------------------------------------------
def _render_sales_report():
    st.markdown("#### Sales Report")
    start_date, end_date = _date_range_inputs("sales_report")

    customers = database.get_all_customers()
    customer_options = {"All": None}
    customer_options.update({c["name"]: c["customer_id"] for c in customers})
    col1, col2 = st.columns(2)
    with col1:
        payment_method = st.selectbox("Payment Method", ["All", "Cash", "UPI", "Debit Card", "Credit"], key="sales_report_pm")
    with col2:
        customer_name = st.selectbox("Customer", list(customer_options.keys()), key="sales_report_customer")

    rows = database.get_sales_report(
        start_date=start_date, end_date=end_date,
        payment_method=payment_method, customer_id=customer_options[customer_name],
    )
    if not rows:
        st.info("No sales found for the selected filters.")
        return

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.caption(f"{len(rows)} bill(s) · Total: {config.CURRENCY_SYMBOL}{df['grand_total'].sum():,.2f}")
    _download_buttons(df, "martiq_sales_report", "sales_report")


# ----------------------------------------------------------------
# BILLING REPORT
# ----------------------------------------------------------------
def _render_billing_report():
    st.markdown("#### Billing Report (Line-Item Detail)")
    start_date, end_date = _date_range_inputs("billing_report")

    rows = database.get_billing_report(start_date=start_date, end_date=end_date)
    if not rows:
        st.info("No billing line items found for the selected date range.")
        return

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.caption(f"{len(rows)} line item(s) · Total: {config.CURRENCY_SYMBOL}{df['line_total'].sum():,.2f}")
    _download_buttons(df, "martiq_billing_report", "billing_report")


# ----------------------------------------------------------------
# PRODUCT REPORT
# ----------------------------------------------------------------
def _render_product_report():
    st.markdown("#### Product Report")
    rows = database.get_all_products()
    if not rows:
        st.info("No products found.")
        return

    df = pd.DataFrame(rows)[["product_id", "name", "category", "price", "supplier", "status"]]
    df.columns = ["ID", "Name", "Category", "Price", "Supplier", "Status"]
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.caption(f"{len(rows)} product(s).")
    _download_buttons(df, "martiq_product_report", "product_report")


# ----------------------------------------------------------------
# INVENTORY REPORT
# ----------------------------------------------------------------
def _render_inventory_report():
    st.markdown("#### Inventory Report")
    rows = database.get_inventory_report()
    if not rows:
        st.info("No products found.")
        return

    df = pd.DataFrame(rows)[["product_id", "name", "category", "stock", "min_stock", "stock_status"]]
    df.columns = ["ID", "Name", "Category", "Stock", "Min Stock", "Status"]
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.caption(f"{len(rows)} product(s).")
    _download_buttons(df, "martiq_inventory_report", "inventory_report")


# ----------------------------------------------------------------
# CUSTOMER REPORT
# ----------------------------------------------------------------
def _render_customer_report():
    st.markdown("#### Customer Report")
    rows = database.get_customer_report()
    if not rows:
        st.info("No customers found.")
        return

    df = pd.DataFrame(rows)[["customer_id", "name", "phone", "membership", "credit_limit", "used_credit", "available_credit", "status"]]
    df.columns = ["ID", "Name", "Phone", "Membership", "Credit Limit", "Used Credit", "Available Credit", "Status"]
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.caption(f"{len(rows)} customer(s).")
    _download_buttons(df, "martiq_customer_report", "customer_report")
