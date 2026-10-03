"""
MARTIQ - Smart Inventory Intelligence Page
----------------------------------------------
"Smart Inventory Recommendations" — a small, fully explainable set
of rules over current stock + recent sales velocity (see
database.get_smart_inventory_table() for the exact rule set). This
is rule-based logic, not a machine learning model, and the page
says so explicitly.
"""

import pandas as pd
import streamlit as st

import config
import database
from utils import ui


def render():
    ui.page_header("🤖", "Smart Inventory", "Rule-Based Inventory Intelligence")

    st.caption(
        "These are **Smart Inventory Recommendations** generated from simple, explainable "
        "rules over current stock and recent sales — not a machine learning model."
    )

    if database.get_product_stats()["total_products"] == 0:
        st.info("No products yet. Add products in the Products module to see recommendations here.")
        return

    days = st.slider("Analyze sales from the last N days", min_value=7, max_value=90, value=30, step=1)

    table = database.get_smart_inventory_table(days=days)

    _render_summary(table)
    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        _render_fast_moving(days)
    with col2:
        _render_slow_moving(days)

    st.markdown("---")
    _render_recommendation_table(table)


def _render_summary(table: list):
    counts = {"🔴 Out of Stock": 0, "🟡 Low Stock": 0, "🟠 Reorder Soon": 0, "🟢 Healthy": 0}
    for row in table:
        counts[row["status"]] = counts.get(row["status"], 0) + 1

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        ui.metric_card("🔴", "Out of Stock", str(counts["🔴 Out of Stock"]))
    with c2:
        ui.metric_card("🟡", "Low Stock", str(counts["🟡 Low Stock"]))
    with c3:
        ui.metric_card("🟠", "Reorder Soon", str(counts["🟠 Reorder Soon"]))
    with c4:
        ui.metric_card("🟢", "Healthy", str(counts["🟢 Healthy"]))


def _render_fast_moving(days: int):
    st.markdown("#### 🚀 Fast-Moving Products")
    rows = database.get_fast_moving_products(limit=5, days=days)
    if not rows:
        st.info(f"No sales in the last {days} days yet.")
        return
    df = pd.DataFrame(rows)[["name", "category", "qty_sold"]]
    df.columns = ["Product", "Category", f"Sold (last {days}d)"]
    st.dataframe(df, use_container_width=True, hide_index=True)


def _render_slow_moving(days: int):
    st.markdown("#### 🐢 Slow-Moving Products")
    rows = database.get_slow_moving_products(limit=5, days=days)
    if not rows:
        st.info("No products to analyze.")
        return
    df = pd.DataFrame(rows)[["name", "category", "stock", "qty_sold"]]
    df.columns = ["Product", "Category", "Current Stock", f"Sold (last {days}d)"]
    st.dataframe(df, use_container_width=True, hide_index=True)


def _render_recommendation_table(table: list):
    st.markdown("#### Restock Recommendations")

    needs_action = [r for r in table if r["recommended_reorder"] > 0]
    if not needs_action:
        st.success("No products currently need restocking based on the selected time window.")
        return

    df = pd.DataFrame(needs_action)[
        ["name", "category", "stock", "min_stock", "recent_sales", "status", "recommended_reorder", "reason"]
    ]
    df.columns = ["Product", "Category", "Current Stock", "Minimum Stock",
                  "Recent Sales", "Status", "Suggested Reorder Qty", "Reason"]
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.caption(
        f"{len(needs_action)} product(s) flagged for reorder out of {len(table)} active product(s). "
        f"Suggested quantities cover roughly two weeks of recent sales pace, or the gap to the "
        f"minimum stock level — whichever is higher."
    )
