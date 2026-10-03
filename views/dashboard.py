"""
MARTIQ - Dashboard Page
--------------------------
PHASE 3.

The live overview screen: KPIs, quick actions, stock/credit alerts,
recent transactions, and a sales trend chart. Every number here
comes from database.py - nothing is hard-coded. Tables that don't
have data yet (Customers/Products/Billing come in later phases)
are handled gracefully with friendly empty states instead of
broken charts or crashes.
"""

from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import config
import database
from utils import ui


def render():
    ui.page_header(
        "🏠",
        "Dashboard",
        f"{config.APP_TAGLINE} · {datetime.now().strftime('%A, %d %B %Y — %I:%M %p')}",
    )

    stats = database.get_dashboard_stats()

    _render_kpi_cards(stats)
    st.markdown("")
    _render_quick_actions()
    st.markdown("---")

    left_col, right_col = st.columns([1, 1.3])
    with left_col:
        _render_alerts_section()
    with right_col:
        _render_recent_transactions()

    st.markdown("---")
    _render_sales_trend()


# ----------------------------------------------------------------
# KPI CARDS
# ----------------------------------------------------------------
def _render_kpi_cards(stats: dict):
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        ui.metric_card("💰", "Total Sales", f"{config.CURRENCY_SYMBOL}{stats['total_sales']:,.2f}")
    with c2:
        ui.metric_card("🧾", "Total Bills", f"{stats['total_bills']:,}")
    with c3:
        ui.metric_card("👥", "Total Customers", f"{stats['total_customers']:,}")
    with c4:
        ui.metric_card("📦", "Total Products", f"{stats['total_products']:,}")

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    c5, c6 = st.columns(2)
    with c5:
        ui.metric_card("🛍️", "Items Sold", f"{stats['items_sold']:,}")
    with c6:
        ui.metric_card("📈", "Average Bill Value", f"{config.CURRENCY_SYMBOL}{stats['avg_bill_value']:,.2f}")


# ----------------------------------------------------------------
# QUICK ACTIONS
# ----------------------------------------------------------------
def _render_quick_actions():
    st.markdown("#### Quick Actions")
    a1, a2, a3, a4 = st.columns(4)

    with a1:
        if st.button("➕ Add Customer", use_container_width=True):
            _go_to("Customers")
    with a2:
        if st.button("➕ Add Product", use_container_width=True):
            _go_to("Products")
    with a3:
        if st.button("🧾 New Bill", use_container_width=True):
            _go_to("Billing")
    with a4:
        if st.button("📊 View Analytics", use_container_width=True):
            _go_to("Analytics")


def _go_to(page_key: str):
    st.session_state[config.SESSION_PAGE] = page_key
    st.rerun()


# ----------------------------------------------------------------
# STOCK + CREDIT ALERTS
# ----------------------------------------------------------------
def _render_alerts_section():
    st.markdown("#### Stock Alerts")

    out_of_stock = database.get_out_of_stock_products()
    low_stock = database.get_low_stock_products()

    if not out_of_stock and not low_stock:
        st.success("All products are sufficiently stocked. No alerts right now.")
    else:
        for p in out_of_stock:
            ui.alert_pill(f"🔴 **{p['name']}** ({p['category']}) — Out of Stock", level="danger")
        for p in low_stock:
            ui.alert_pill(
                f"🟡 **{p['name']}** ({p['category']}) — Low Stock: {p['stock']} left "
                f"(min {p['min_stock']})",
                level="warning",
            )

    if database.get_dashboard_stats()["total_products"] == 0:
        st.caption("No products in the system yet. Add products in Phase 5 to see stock alerts here.")

    st.markdown("#### Credit Alerts")
    credit_alerts = database.get_credit_alerts()

    if not credit_alerts:
        st.success("No customers are near their credit limit.")
    else:
        for a in credit_alerts:
            ui.alert_pill(
                f"⚠️ **{a['name']}** ({a['phone']}) — {a['usage_pct']:.0f}% of credit used "
                f"({config.CURRENCY_SYMBOL}{a['used_credit']:,.0f} / "
                f"{config.CURRENCY_SYMBOL}{a['credit_limit']:,.0f})",
                level="danger" if a["usage_pct"] >= 100 else "warning",
            )


# ----------------------------------------------------------------
# RECENT TRANSACTIONS
# ----------------------------------------------------------------
def _render_recent_transactions():
    st.markdown("#### Recent Transactions")

    transactions = database.get_recent_transactions()

    if not transactions:
        st.info(
            "No transactions yet. Once Billing is built (Phase 6) and bills are "
            "created, the most recent ones will appear here automatically."
        )
        return

    df = pd.DataFrame(transactions)
    df["bill_date"] = pd.to_datetime(df["bill_date"]).dt.strftime("%d %b %Y, %I:%M %p")
    df["grand_total"] = df["grand_total"].apply(lambda v: f"{config.CURRENCY_SYMBOL}{v:,.2f}")
    df = df.rename(columns={
        "invoice_number": "Invoice #",
        "customer_name": "Customer",
        "bill_date": "Date",
        "grand_total": "Amount",
        "payment_method": "Payment",
    })[["Invoice #", "Customer", "Date", "Amount", "Payment"]]

    st.dataframe(df, use_container_width=True, hide_index=True)


# ----------------------------------------------------------------
# SALES TREND
# ----------------------------------------------------------------
def _render_sales_trend():
    st.markdown("#### Sales Trend")

    total_bills = database.get_dashboard_stats()["total_bills"]
    if total_bills == 0:
        st.info(
            "No sales data yet. Once Billing (Phase 6) is built and bills start "
            "coming in, daily and monthly sales trends will appear here."
        )
        return

    tab_daily, tab_monthly = st.tabs(["📅 Daily (Last 14 Days)", "🗓️ Monthly (Last 6 Months)"])

    with tab_daily:
        daily = database.get_daily_sales_trend(days=14)
        _render_trend_chart(daily, x_title="Day")

    with tab_monthly:
        monthly = database.get_monthly_sales_trend(months=6)
        _render_trend_chart(monthly, x_title="Month")


def _render_trend_chart(data: list, x_title: str):
    labels = [row[0] for row in data]
    values = [row[1] for row in data]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=labels,
            y=values,
            mode="lines+markers",
            line=dict(color=config.THEME["primary"], width=3),
            marker=dict(size=7, color=config.THEME["primary_light"]),
            fill="tozeroy",
            fillcolor="rgba(46, 204, 113, 0.15)",
        )
    )
    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
        height=320,
        xaxis_title=x_title,
        yaxis_title=f"Sales ({config.CURRENCY_SYMBOL})",
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    st.plotly_chart(fig, use_container_width=True)
