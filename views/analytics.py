"""
MARTIQ - Analytics Page
--------------------------
Sales analytics driven entirely by database.py queries, with date
range and category filters. Every chart checks for empty data first
and shows a friendly message instead of drawing a meaningless chart.
"""

from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

import config
import database
from utils import ui


def render():
    ui.page_header("📊", "Analytics", "Sales trends, top products, and spending insights")

    stats = database.get_dashboard_stats()
    if stats["total_bills"] == 0:
        st.info(
            "No sales data yet. Once bills are created in **Billing**, sales trends, "
            "top products, and spending insights will appear here automatically."
        )
        _render_stock_overview()
        return

    start_date, end_date, category = _render_filters()

    _render_sales_over_time(start_date, end_date)
    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        _render_top_products(start_date, end_date, category)
    with col2:
        _render_category_sales(start_date, end_date)

    st.markdown("---")

    col3, col4 = st.columns(2)
    with col3:
        _render_payment_distribution(start_date, end_date)
    with col4:
        _render_top_customers(start_date, end_date)

    st.markdown("---")
    _render_bill_value_distribution(start_date, end_date)
    st.markdown("---")
    _render_stock_overview()


# ----------------------------------------------------------------
# FILTERS
# ----------------------------------------------------------------
def _render_filters():
    st.markdown("#### Filters")
    col1, col2, col3 = st.columns([1.3, 1.3, 1])

    with col1:
        default_start = date.today() - timedelta(days=30)
        start_date = st.date_input("From", value=default_start, key="analytics_start")
    with col2:
        end_date = st.date_input("To", value=date.today(), key="analytics_end")
    with col3:
        categories = ["All"] + database.get_categories()
        category = st.selectbox("Category", categories, key="analytics_category")

    return start_date.isoformat(), end_date.isoformat(), category


# ----------------------------------------------------------------
# CHARTS
# ----------------------------------------------------------------
def _render_sales_over_time(start_date, end_date):
    st.markdown("#### Sales Over Time")
    data = database.get_sales_over_time(start_date, end_date)
    if not data:
        st.info("No sales in the selected date range.")
        return

    df = pd.DataFrame(data, columns=["Date", "Sales"])
    fig = px.line(df, x="Date", y="Sales", markers=True)
    fig.update_traces(line_color=config.THEME["primary"], fillpattern_shape="")
    fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10), yaxis_title=f"Sales ({config.CURRENCY_SYMBOL})")
    st.plotly_chart(fig, use_container_width=True)


def _render_top_products(start_date, end_date, category):
    st.markdown("#### Top-Selling Products")
    data = database.get_top_selling_products(limit=10, start_date=start_date, end_date=end_date, category=category)
    if not data:
        st.info("No product sales in the selected range/category.")
        return

    df = pd.DataFrame(data)
    fig = px.bar(df, x="total_qty", y="name", orientation="h", color_discrete_sequence=[config.THEME["primary"]])
    fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10), xaxis_title="Units Sold", yaxis_title="")
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(fig, use_container_width=True)


def _render_category_sales(start_date, end_date):
    st.markdown("#### Category-Wise Sales")
    data = database.get_category_sales(start_date, end_date)
    if not data:
        st.info("No category sales in the selected range.")
        return

    df = pd.DataFrame(data)
    fig = px.pie(df, names="category", values="total_revenue", hole=0.45,
                 color_discrete_sequence=px.colors.sequential.Greens_r)
    fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)


def _render_payment_distribution(start_date, end_date):
    st.markdown("#### Payment Method Distribution")
    data = database.get_payment_method_distribution(start_date, end_date)
    if not data:
        st.info("No payments in the selected range.")
        return

    df = pd.DataFrame(data)
    fig = px.pie(df, names="payment_method", values="total", hole=0.45,
                 color_discrete_sequence=px.colors.sequential.Greens_r)
    fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)


def _render_top_customers(start_date, end_date):
    st.markdown("#### Customer Spending (Top 10)")
    data = database.get_top_customers(limit=10, start_date=start_date, end_date=end_date)
    if not data:
        st.info("No customer purchases in the selected range.")
        return

    df = pd.DataFrame(data)
    fig = px.bar(df, x="total_spent", y="name", orientation="h", color_discrete_sequence=[config.THEME["primary_light"]])
    fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10), xaxis_title=f"Spent ({config.CURRENCY_SYMBOL})", yaxis_title="")
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(fig, use_container_width=True)


def _render_bill_value_distribution(start_date, end_date):
    st.markdown("#### Bill Value Distribution")
    values = database.get_bill_value_list(start_date, end_date)
    if not values:
        st.info("No bills in the selected range.")
        return

    df = pd.DataFrame({"Bill Value": values})
    fig = px.histogram(df, x="Bill Value", nbins=min(20, max(5, len(values))),
                        color_discrete_sequence=[config.THEME["primary"]])
    fig.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="Number of Bills")
    st.plotly_chart(fig, use_container_width=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("Average Bill", f"{config.CURRENCY_SYMBOL}{sum(values)/len(values):,.2f}")
    c2.metric("Highest Bill", f"{config.CURRENCY_SYMBOL}{max(values):,.2f}")
    c3.metric("Lowest Bill", f"{config.CURRENCY_SYMBOL}{min(values):,.2f}")


def _render_stock_overview():
    st.markdown("#### Stock Overview")
    overview = database.get_stock_overview()
    if sum(overview.values()) == 0:
        st.info("No products yet. Add products in the Products module to see a stock overview here.")
        return

    df = pd.DataFrame({"Status": list(overview.keys()), "Count": list(overview.values())})
    fig = px.bar(df, x="Status", y="Count",
                 color="Status",
                 color_discrete_map={"In Stock": config.THEME["success"], "Low Stock": config.THEME["warning"], "Out of Stock": config.THEME["danger"]})
    fig.update_layout(height=280, margin=dict(l=10, r=10, t=10, b=10), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
