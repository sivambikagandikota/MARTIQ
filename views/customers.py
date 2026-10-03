"""
MARTIQ - Customer Management Page
------------------------------------
PHASE 4.

Full CRUD for the `customers` table: summary cards, searchable/
filterable table, add form, and edit/delete with a safe two-step
delete confirmation. Deletion is blocked if the customer already
has bills, to protect the bills.customer_id foreign key.
"""

import pandas as pd
import streamlit as st

import config
import database
from utils import ui, validators

MEMBERSHIP_OPTIONS = ["Regular", "Silver", "Gold", "Platinum"]
STATUS_OPTIONS = ["Active", "Inactive"]


def render():
    ui.page_header("👥", "Customer Management", "Add, view, search, edit, and manage customer records")

    stats = database.get_customer_stats()
    c1, c2 = st.columns(2)
    with c1:
        ui.metric_card("👥", "Total Customers", f"{stats['total_customers']:,}")
    with c2:
        ui.metric_card("✅", "Active Customers", f"{stats['active_customers']:,}")

    st.markdown("")

    tab_view, tab_add, tab_bulk, tab_edit = st.tabs(["📋 View Customers", "➕ Add Customer", "📥 Bulk Upload", "✏️ Edit / Delete Customer"])
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
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        search = st.text_input("🔍 Search by ID, name, or phone", key="cust_search")
    with col2:
        membership_filter = st.selectbox("Membership", ["All"] + MEMBERSHIP_OPTIONS, key="cust_membership_filter")
    with col3:
        status_filter = st.selectbox("Status", ["All"] + STATUS_OPTIONS, key="cust_status_filter")

    customers = database.get_all_customers(
        search=search, membership_filter=membership_filter, status_filter=status_filter
    )

    if not customers:
        if search or membership_filter != "All" or status_filter != "All":
            st.info("No customers match your search/filters.")
        else:
            st.info("No customers yet. Add your first customer in the **Add Customer** tab.")
        return

    df = pd.DataFrame(customers)
    df["credit_limit"] = df["credit_limit"].apply(lambda v: f"{config.CURRENCY_SYMBOL}{v:,.2f}")
    df["used_credit"] = df["used_credit"].apply(lambda v: f"{config.CURRENCY_SYMBOL}{v:,.2f}")
    df["available_credit"] = df["available_credit"].apply(lambda v: f"{config.CURRENCY_SYMBOL}{v:,.2f}")

    df = df.rename(columns={
        "customer_id": "ID",
        "name": "Name",
        "phone": "Phone",
        "email": "Email",
        "address": "Address",
        "membership": "Membership",
        "credit_limit": "Credit Limit",
        "used_credit": "Used Credit",
        "available_credit": "Available Credit",
        "status": "Status",
    })[["ID", "Name", "Phone", "Email", "Address", "Membership",
        "Credit Limit", "Used Credit", "Available Credit", "Status"]]

    st.dataframe(df, use_container_width=True, hide_index=True)
    st.caption(f"Showing {len(customers)} customer(s).")


# ----------------------------------------------------------------
# ADD
# ----------------------------------------------------------------
def _render_add_tab():
    st.markdown("#### Add a New Customer")

    with st.form("add_customer_form", clear_on_submit=True):
        name = st.text_input("Name*", placeholder="e.g. Ravi Kumar")

        col1, col2 = st.columns(2)
        with col1:
            phone = st.text_input("Phone*", placeholder="10-digit mobile number")
        with col2:
            email = st.text_input("Email", placeholder="optional")

        address = st.text_area("Address", placeholder="optional", height=80)

        col3, col4 = st.columns(2)
        with col3:
            membership = st.selectbox("Membership", MEMBERSHIP_OPTIONS)
        with col4:
            credit_limit = st.number_input("Credit Limit", min_value=0.0, step=500.0, value=0.0)

        submitted = st.form_submit_button("➕ Add Customer", use_container_width=True)

    if submitted:
        errors = validators.validate_customer_form(name, phone, email)
        if errors:
            for err in errors:
                st.error(err)
            return

        success, result = database.add_customer(
            name.strip(), phone.strip(), email.strip(), address.strip(), membership, credit_limit
        )
        if success:
            st.success(f"Customer **{name.strip()}** added successfully (ID: {result}).")
        else:
            st.error(result)


# ----------------------------------------------------------------
# BULK UPLOAD
# ----------------------------------------------------------------
def _render_bulk_tab():
    st.markdown("#### Bulk Customer Upload")
    template = pd.DataFrame([{
        "Name":"Ravi Kumar", "Phone":"9876543210", "Email":"ravi@example.com",
        "Address":"Hyderabad", "Membership":"Regular", "Credit Limit":0
    }])
    st.download_button("📥 Download Customer Template", template.to_csv(index=False).encode("utf-8"), "martiq_customer_template.csv", "text/csv", use_container_width=True)
    uploaded=st.file_uploader("Upload Customers (CSV/XLSX)", type=["csv","xlsx"], key="customer_bulk_upload")
    if not uploaded: return
    try:
        df=pd.read_csv(uploaded) if uploaded.name.lower().endswith(".csv") else pd.read_excel(uploaded)
        st.dataframe(df.head(20), use_container_width=True, hide_index=True)
        if st.button("✅ Import Customers", key="import_customers_btn", type="primary"):
            result=database.bulk_import_customers(df)
            st.success(f"Imported: {result['success']} · Failed: {result['failed']} · Duplicates: {result['duplicates']}")
            for err in result["errors"][:10]: st.warning(err)
            st.rerun()
    except Exception as e:
        st.error(f"Could not read the file: {e}")


# ----------------------------------------------------------------
# EDIT / DELETE
# ----------------------------------------------------------------
def _render_edit_delete_tab():
    customers = database.get_all_customers()
    if not customers:
        st.info("No customers yet. Add one in the **Add Customer** tab first.")
        return

    options = {f"#{c['customer_id']} — {c['name']} ({c['phone']})": c["customer_id"] for c in customers}
    selected_label = st.selectbox("Select a customer to edit or delete", list(options.keys()), key="cust_edit_select")
    selected_id = options[selected_label]

    customer = database.get_customer_by_id(selected_id)
    if not customer:
        st.error("This customer no longer exists. Please refresh the selection.")
        return

    st.markdown("##### Edit Details")
    with st.form(f"edit_customer_form_{selected_id}"):
        name = st.text_input("Name*", value=customer["name"])

        col1, col2 = st.columns(2)
        with col1:
            phone = st.text_input("Phone*", value=customer["phone"])
        with col2:
            email = st.text_input("Email", value=customer["email"] or "")

        address = st.text_area("Address", value=customer["address"] or "", height=80)

        col3, col4, col5 = st.columns(3)
        with col3:
            membership = st.selectbox("Membership", MEMBERSHIP_OPTIONS, index=MEMBERSHIP_OPTIONS.index(customer["membership"]))
        with col4:
            credit_limit = st.number_input("Credit Limit", min_value=0.0, step=500.0, value=float(customer["credit_limit"]))
        with col5:
            status = st.selectbox("Status", STATUS_OPTIONS, index=STATUS_OPTIONS.index(customer["status"]))

        save_clicked = st.form_submit_button("💾 Save Changes", use_container_width=True)

    if save_clicked:
        errors = validators.validate_customer_form(name, phone, email)
        if errors:
            for err in errors:
                st.error(err)
        else:
            success, message = database.update_customer(
                selected_id, name.strip(), phone.strip(), email.strip(),
                address.strip(), membership, credit_limit, status,
            )
            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)

    st.markdown("---")
    st.markdown("##### Danger Zone")
    available = customer["credit_limit"] - customer["used_credit"]
    st.caption(
        f"Used Credit: {config.CURRENCY_SYMBOL}{customer['used_credit']:,.2f} · "
        f"Available Credit: {config.CURRENCY_SYMBOL}{available:,.2f}"
    )

    confirm_key = f"confirm_delete_{selected_id}"
    if st.session_state.get(confirm_key, False):
        st.warning(f"Are you sure you want to permanently delete **{customer['name']}**? This cannot be undone.")
        col_yes, col_no = st.columns(2)
        with col_yes:
            if st.button("✅ Yes, Delete", key=f"confirm_yes_{selected_id}", use_container_width=True):
                success, message = database.delete_customer(selected_id)
                st.session_state[confirm_key] = False
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
        with col_no:
            if st.button("Cancel", key=f"confirm_no_{selected_id}", use_container_width=True):
                st.session_state[confirm_key] = False
                st.rerun()
    else:
        if st.button("🗑️ Delete Customer", key=f"delete_btn_{selected_id}"):
            st.session_state[confirm_key] = True
            st.rerun()
