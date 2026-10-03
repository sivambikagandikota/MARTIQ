"""
MARTIQ - Product & Inventory Management Page
-------------------------------------------------
Full CRUD for the `products` table: summary cards, searchable/
filterable table with stock-status indicators, add form, and
edit/delete with a safe two-step delete confirmation. Deletion is
blocked if the product already appears on a bill, to protect the
bill_items.product_id foreign key.
"""

import pandas as pd
import streamlit as st

import config
import database
from utils import ui

STATUS_OPTIONS = ["Active", "Discontinued"]


def render():
    ui.page_header("📦", "Product Management", "Manage inventory, pricing, and stock levels")

    stats = database.get_product_stats()
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        ui.metric_card("📦", "Total Products", f"{stats['total_products']:,}")
    with c2:
        ui.metric_card("🟢", "Healthy Stock", f"{stats['healthy_stock']:,}")
    with c3:
        ui.metric_card("🟡", "Low Stock", f"{stats['low_stock']:,}")
    with c4:
        ui.metric_card("🔴", "Out of Stock", f"{stats['out_of_stock']:,}")

    st.markdown("")

    tab_view, tab_add, tab_bulk, tab_edit = st.tabs(["📋 View Products", "➕ Add Product", "📥 Bulk Upload", "✏️ Edit / Delete Product"])
    with tab_view:
        _render_view_tab()
    with tab_add:
        _render_add_tab()
    with tab_bulk:
        _render_bulk_tab()
    with tab_edit:
        _render_edit_delete_tab()


# ----------------------------------------------------------------
# VIEW / SEARCH
# ----------------------------------------------------------------
def _render_view_tab():
    categories = ["All"] + database.get_categories()

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        search = st.text_input("🔍 Search by ID or name", key="prod_search")
    with col2:
        category_filter = st.selectbox("Category", categories, key="prod_category_filter")
    with col3:
        status_filter = st.selectbox("Status", ["All"] + STATUS_OPTIONS, key="prod_status_filter")

    products = database.get_all_products(search=search, category_filter=category_filter, status_filter=status_filter)

    if not products:
        if search or category_filter != "All" or status_filter != "All":
            st.info("No products match your search/filters.")
        else:
            st.info("No products yet. Add your first product in the **Add Product** tab.")
        return

    df = pd.DataFrame(products)
    df["price"] = df["price"].apply(lambda v: f"{config.CURRENCY_SYMBOL}{v:,.2f}")
    df["gst_percent"] = df["gst_percent"].apply(lambda v: f"{v:g}%")

    df = df.rename(columns={
        "product_id": "ID",
        "name": "Name",
        "category": "Category",
        "price": "Price",
        "stock": "Stock",
        "min_stock": "Min Stock",
        "gst_percent": "GST",
        "supplier": "Supplier",
        "barcode": "Barcode",
        "status": "Status",
        "stock_status": "Stock Health",
    })[["ID", "Name", "Category", "Price", "Stock", "Min Stock", "GST", "Supplier", "Barcode", "Status", "Stock Health"]]

    st.dataframe(df, use_container_width=True, hide_index=True)
    st.caption(f"Showing {len(products)} product(s).")


# ----------------------------------------------------------------
# ADD
# ----------------------------------------------------------------
def _render_add_tab():
    st.markdown("#### Add a New Product")

    with st.form("add_product_form", clear_on_submit=True):
        name = st.text_input("Product Name*", placeholder="e.g. Rice 5kg")

        col1, col2 = st.columns(2)
        with col1:
            category = st.text_input("Category*", placeholder="e.g. Grocery")
        with col2:
            supplier = st.text_input("Supplier", placeholder="optional")

        col3, col4, col5 = st.columns(3)
        with col3:
            price = st.number_input("Price*", min_value=0.0, step=1.0, value=0.0)
        with col4:
            stock = st.number_input("Opening Stock", min_value=0, step=1, value=0)
        with col5:
            min_stock = st.number_input("Minimum Stock Level*", min_value=0, step=1, value=5)

        gst_percent = st.number_input(
            "GST %", min_value=0.0, max_value=100.0, step=0.5, value=config.DEFAULT_GST_PERCENT
        )
        barcode = st.text_input("Barcode (optional)", placeholder="Scan/type barcode; auto-generated if blank")

        submitted = st.form_submit_button("➕ Add Product", use_container_width=True)

    if submitted:
        errors = _validate_product_form(name, category, price, min_stock)
        if errors:
            for err in errors:
                st.error(err)
            return

        success, result = database.add_product(
            name.strip(), category.strip(), price, int(stock), int(min_stock), gst_percent, supplier.strip(), barcode.strip()
        )
        if success:
            st.success(f"Product **{name.strip()}** added successfully (ID: {result}).")
        else:
            st.error(result)


def _validate_product_form(name, category, price, min_stock):
    errors = []
    if not name or not name.strip():
        errors.append("Product name is required.")
    if not category or not category.strip():
        errors.append("Category is required.")
    if price < 0:
        errors.append("Price cannot be negative.")
    if min_stock < 0:
        errors.append("Minimum stock level cannot be negative.")
    return errors


# ----------------------------------------------------------------
# BULK UPLOAD
# ----------------------------------------------------------------
def _render_bulk_tab():
    st.markdown("#### Bulk Product Upload")
    template = pd.DataFrame([{
        "Product Name":"Rice 5kg", "Category":"Grocery", "Supplier":"Supplier Name",
        "Price":320, "Opening Stock":50, "Minimum Stock Level":10, "GST %":5, "Barcode":"890000000001"
    }])
    st.download_button("📥 Download Product Template", template.to_csv(index=False).encode("utf-8"), "martiq_product_template.csv", "text/csv", use_container_width=True)
    uploaded = st.file_uploader("Upload Products (CSV/XLSX)", type=["csv","xlsx"], key="product_bulk_upload")
    if not uploaded: return
    try:
        df = pd.read_csv(uploaded) if uploaded.name.lower().endswith(".csv") else pd.read_excel(uploaded)
        st.markdown("##### Preview")
        st.dataframe(df.head(20), use_container_width=True, hide_index=True)
        if st.button("✅ Import Products", key="import_products_btn", type="primary"):
            result=database.bulk_import_products(df)
            st.success(f"Imported: {result['success']} · Failed: {result['failed']} · Duplicates: {result['duplicates']}")
            for err in result["errors"][:10]: st.warning(err)
            st.rerun()
    except Exception as e:
        st.error(f"Could not read the file: {e}")


# ----------------------------------------------------------------
# EDIT / DELETE
# ----------------------------------------------------------------
def _render_edit_delete_tab():
    products = database.get_all_products()
    if not products:
        st.info("No products yet. Add one in the **Add Product** tab first.")
        return

    options = {f"#{p['product_id']} — {p['name']} ({p['category']})": p["product_id"] for p in products}
    selected_label = st.selectbox("Select a product to edit or delete", list(options.keys()), key="prod_edit_select")
    selected_id = options[selected_label]

    product = database.get_product_by_id(selected_id)
    if not product:
        st.error("This product no longer exists. Please refresh the selection.")
        return

    st.markdown("##### Edit Details")
    with st.form(f"edit_product_form_{selected_id}"):
        name = st.text_input("Product Name*", value=product["name"])

        col1, col2 = st.columns(2)
        with col1:
            category = st.text_input("Category*", value=product["category"])
        with col2:
            supplier = st.text_input("Supplier", value=product["supplier"] or "")

        col3, col4, col5 = st.columns(3)
        with col3:
            price = st.number_input("Price*", min_value=0.0, step=1.0, value=float(product["price"]))
        with col4:
            stock = st.number_input("Stock*", min_value=0, step=1, value=int(product["stock"]))
        with col5:
            min_stock = st.number_input("Minimum Stock Level*", min_value=0, step=1, value=int(product["min_stock"]))

        col6, col7 = st.columns(2)
        with col6:
            gst_percent = st.number_input(
                "GST %", min_value=0.0, max_value=100.0, step=0.5, value=float(product["gst_percent"])
            )
        with col7:
            status = st.selectbox("Status", STATUS_OPTIONS, index=STATUS_OPTIONS.index(product["status"]))
        barcode = st.text_input("Barcode", value=product.get("barcode") or "")

        save_clicked = st.form_submit_button("💾 Save Changes", use_container_width=True)

    if save_clicked:
        errors = _validate_product_form(name, category, price, min_stock)
        if errors:
            for err in errors:
                st.error(err)
        else:
            success, message = database.update_product(
                selected_id, name.strip(), category.strip(), price, int(stock),
                int(min_stock), gst_percent, supplier.strip(), status, barcode.strip(),
            )
            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)

    st.markdown("---")
    st.markdown("##### Danger Zone")

    confirm_key = f"confirm_delete_product_{selected_id}"
    if st.session_state.get(confirm_key, False):
        st.warning(f"Are you sure you want to permanently delete **{product['name']}**? This cannot be undone.")
        col_yes, col_no = st.columns(2)
        with col_yes:
            if st.button("✅ Yes, Delete", key=f"confirm_yes_prod_{selected_id}", use_container_width=True):
                success, message = database.delete_product(selected_id)
                st.session_state[confirm_key] = False
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
        with col_no:
            if st.button("Cancel", key=f"confirm_no_prod_{selected_id}", use_container_width=True):
                st.session_state[confirm_key] = False
                st.rerun()
    else:
        if st.button("🗑️ Delete Product", key=f"delete_btn_prod_{selected_id}"):
            st.session_state[confirm_key] = True
            st.rerun()
