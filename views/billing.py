"""
MARTIQ - Billing / POS Page
------------------------------
Cart-based point-of-sale: pick a customer (or Walk-in Customer),
add products to a cart held in session state, adjust quantities,
apply a discount, choose a payment method, and generate the bill.

database.create_bill() does all of the real work atomically: it
re-validates stock, checks the customer's credit limit for Credit
payments, inserts the bill + bill_items, decrements product stock,
updates used_credit, and records a payment — all on one connection,
so a failure midway rolls back everything instead of leaving the
database half-updated.

After a successful bill, a receipt is shown with Print and Download
options and the cart is cleared, ready for the next sale.
"""

import streamlit as st
from streamlit.components.v1 import html as st_html

import config
import database
from utils import ui

PAYMENT_METHODS = ["Cash", "UPI", "Debit Card", "Credit"]
_LAST_BILL_KEY = "martiq_last_bill_id"


def render():
    ui.page_header("🧾", "Billing / POS", "Create new bills and generate invoices")

    if st.session_state.get(_LAST_BILL_KEY):
        _render_receipt(st.session_state[_LAST_BILL_KEY])
        if st.button("🧾 Start a New Bill"):
            st.session_state[_LAST_BILL_KEY] = None
            st.rerun()
        return

    if config.SESSION_CART not in st.session_state or st.session_state[config.SESSION_CART] is None:
        st.session_state[config.SESSION_CART] = []

    products = database.get_all_products(status_filter="Active")
    customers = database.get_billable_customers()

    if not products:
        st.info("No active products available to bill. Add products in the **Products** module first.")
        return
    if not customers:
        st.error("No customers available — this shouldn't happen since Walk-in Customer is seeded automatically.")
        return

    left_col, right_col = st.columns([1.4, 1])
    with left_col:
        _render_barcode_scanner(products)
        _render_product_picker(products)
        st.markdown("---")
        _render_cart(products)
    with right_col:
        _render_checkout(customers)


# ----------------------------------------------------------------
# BARCODE SCANNER
# ----------------------------------------------------------------
def _render_barcode_scanner(products: list):
    st.markdown("#### 🔎 Barcode Scanner")
    st.caption("USB barcode scanners work like a keyboard: scan into the field and press Enter. You can also upload a barcode image.")
    with st.form("barcode_scan_form", clear_on_submit=True):
        code = st.text_input("Scan / enter barcode", placeholder="e.g. 890000000001", key="billing_barcode_input")
        submitted = st.form_submit_button("➕ Add Scanned Product", use_container_width=True)
    if submitted and code.strip():
        product = database.get_product_by_barcode(code.strip())
        if not product:
            st.error(f"No active product found for barcode: {code.strip()}")
        elif product["stock"] <= 0:
            st.error(f"{product['name']} is out of stock.")
        else:
            _add_to_cart(product, 1)
            st.success(f"Added {product['name']} to cart.")
            st.rerun()

    with st.expander("📷 Scan from barcode image"):
        image = st.camera_input("Take a barcode photo", key="billing_barcode_camera")
        if image is not None:
            try:
                import cv2, numpy as np
                data = np.frombuffer(image.getvalue(), dtype=np.uint8)
                frame = cv2.imdecode(data, cv2.IMREAD_COLOR)
                detector = cv2.barcode_BarcodeDetector()
                decoded, points, _ = detector.detectAndDecode(frame)
                code = decoded if isinstance(decoded, str) else (decoded[0] if decoded else "")
                if code:
                    product = database.get_product_by_barcode(code)
                    if product and product["stock"] > 0:
                        _add_to_cart(product, 1); st.success(f"Scanned {code} → {product['name']}"); st.rerun()
                    elif product:
                        st.error(f"{product['name']} is out of stock.")
                    else:
                        st.warning(f"Barcode {code} is not linked to an active product.")
                else:
                    st.info("No barcode detected. Try a clearer, well-lit image.")
            except Exception as e:
                st.info(f"Image scanning is unavailable in this environment: {e}")


# ----------------------------------------------------------------
# PRODUCT PICKER
# ----------------------------------------------------------------
def _render_product_picker(products: list):
    st.markdown("#### Add Products")

    sellable = [p for p in products if p["stock"] > 0]
    if not sellable:
        st.warning("All active products are out of stock. Restock in the Products module.")
        return

    options = {f"{p['name']} — {config.CURRENCY_SYMBOL}{p['price']:,.2f} ({p['stock']} in stock)": p for p in sellable}
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        selected_label = st.selectbox("Product", list(options.keys()), key="billing_product_select")
    with col2:
        product = options[selected_label]
        qty = st.number_input("Qty", min_value=1, max_value=int(product["stock"]), value=1, key="billing_qty_input")
    with col3:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        add_clicked = st.button("➕ Add to Cart", use_container_width=True)

    if add_clicked:
        _add_to_cart(product, qty)
        st.rerun()


def _add_to_cart(product: dict, qty: int):
    cart = st.session_state[config.SESSION_CART]
    for line in cart:
        if line["product_id"] == product["product_id"]:
            new_qty = line["quantity"] + qty
            if new_qty > product["stock"]:
                st.error(f"Only {product['stock']} of '{product['name']}' in stock.")
                return
            line["quantity"] = new_qty
            return
    cart.append({
        "product_id": product["product_id"],
        "name": product["name"],
        "unit_price": product["price"],
        "gst_percent": product["gst_percent"],
        "quantity": qty,
    })


# ----------------------------------------------------------------
# CART
# ----------------------------------------------------------------
def _render_cart(products: list):
    st.markdown("#### Cart")
    cart = st.session_state[config.SESSION_CART]

    if not cart:
        st.info("Cart is empty. Add products above to start a bill.")
        return

    stock_by_id = {p["product_id"]: p["stock"] for p in products}

    for line in list(cart):
        pid = line["product_id"]
        max_stock = stock_by_id.get(pid, line["quantity"])
        col1, col2, col3, col4 = st.columns([3, 1.2, 1.5, 0.8])
        with col1:
            st.write(f"**{line['name']}**")
            st.caption(f"{config.CURRENCY_SYMBOL}{line['unit_price']:,.2f} · GST {line['gst_percent']:g}%")
        with col2:
            new_qty = st.number_input(
                "Qty", min_value=1, max_value=max(max_stock, line["quantity"]),
                value=line["quantity"], key=f"cart_qty_{pid}", label_visibility="collapsed",
            )
            line["quantity"] = new_qty
        with col3:
            line_total = line["unit_price"] * line["quantity"] * (1 + line["gst_percent"] / 100)
            st.write(f"{config.CURRENCY_SYMBOL}{line_total:,.2f}")
        with col4:
            if st.button("🗑️", key=f"cart_remove_{pid}"):
                cart.remove(line)
                st.rerun()


# ----------------------------------------------------------------
# CHECKOUT
# ----------------------------------------------------------------
def _render_checkout(customers: list):
    st.markdown("#### Checkout")

    customer_options = {
        (config.WALKIN_CUSTOMER_NAME if c["phone"] == config.WALKIN_CUSTOMER_PHONE else f"{c['name']} ({c['phone']})"): c
        for c in customers
    }
    selected_customer_label = st.selectbox("Customer", list(customer_options.keys()), key="billing_customer_select")
    customer = customer_options[selected_customer_label]

    if customer["phone"] != config.WALKIN_CUSTOMER_PHONE:
        available_credit = customer["credit_limit"] - customer["used_credit"]
        st.caption(
            f"Available credit: {config.CURRENCY_SYMBOL}{available_credit:,.2f} "
            f"(limit {config.CURRENCY_SYMBOL}{customer['credit_limit']:,.2f})"
        )

    cart = st.session_state[config.SESSION_CART]
    subtotal = sum(l["unit_price"] * l["quantity"] for l in cart)
    gst_amount = sum(l["unit_price"] * l["quantity"] * (l["gst_percent"] / 100) for l in cart)

    discount = st.number_input("Discount", min_value=0.0, step=10.0, value=0.0)
    payment_method = st.radio("Payment Method", PAYMENT_METHODS, horizontal=True)

    grand_total = max(0.0, subtotal - discount + gst_amount)

    st.markdown("---")
    st.write(f"Subtotal: **{config.CURRENCY_SYMBOL}{subtotal:,.2f}**")
    st.write(f"GST: **{config.CURRENCY_SYMBOL}{gst_amount:,.2f}**")
    st.write(f"Discount: **-{config.CURRENCY_SYMBOL}{discount:,.2f}**")
    st.markdown(f"### Grand Total: {config.CURRENCY_SYMBOL}{grand_total:,.2f}")

    st.markdown("")
    if st.button("✅ Generate Bill", use_container_width=True, type="primary", disabled=not cart):
        success, result = database.create_bill(
            customer_id=customer["customer_id"],
            cart_items=cart,
            discount=discount,
            payment_method=payment_method,
        )
        if success:
            st.session_state[config.SESSION_CART] = []
            st.session_state[_LAST_BILL_KEY] = result["bill_id"]
            st.success(f"Bill {result['invoice_number']} generated successfully.")
            st.rerun()
        else:
            st.error(result)


# ----------------------------------------------------------------
# RECEIPT
# ----------------------------------------------------------------
def _render_receipt(bill_id: int):
    bill = database.get_bill_details(bill_id)
    if not bill:
        st.error("This bill could not be found.")
        return

    st.success(f"Bill {bill['invoice_number']} was generated successfully.")
    st.markdown("#### 🧾 Receipt")

    st.markdown('<div class="martiq-card">', unsafe_allow_html=True)
    st.markdown(f"**{config.APP_NAME}**")
    st.caption(config.APP_TAGLINE)
    st.write(f"Invoice #: **{bill['invoice_number']}**")
    st.write(f"Date/Time: {_format_datetime(bill['bill_date'])}")
    st.write(f"Customer: {bill['customer_name']}" + (f" ({bill['customer_phone']})" if bill['customer_phone'] else ""))

    st.markdown("---")
    for item in bill["items"]:
        st.write(
            f"{item['product_name']} — Qty {item['quantity']} × "
            f"{config.CURRENCY_SYMBOL}{item['unit_price']:,.2f} + GST {config.CURRENCY_SYMBOL}{item['gst_amount']:,.2f} "
            f"= **{config.CURRENCY_SYMBOL}{item['line_total']:,.2f}**"
        )

    st.markdown("---")
    st.write(f"Subtotal: {config.CURRENCY_SYMBOL}{bill['subtotal']:,.2f}")
    st.write(f"Discount: -{config.CURRENCY_SYMBOL}{bill['discount']:,.2f}")
    st.write(f"GST: {config.CURRENCY_SYMBOL}{bill['gst_amount']:,.2f}")
    st.markdown(f"**Grand Total: {config.CURRENCY_SYMBOL}{bill['grand_total']:,.2f}**")
    st.write(f"Payment Method: {bill['payment_method']}")

    st.markdown("---")
    st.markdown(
        "Thank You for Shopping with MARTIQ! ❤️  \n"
        "We value your shopping.  \n"
        "Visit MARTIQ Again! 🛒  \n"
        "Have a wonderful day! 😊"
    )
    st.markdown("</div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st_html(
            """
            <button onclick="window.parent.print()"
                style="width:100%; padding:10px; border-radius:8px; border:1px solid #1E8449;
                       background:white; color:#1E8449; font-weight:600; cursor:pointer;">
                🖨️ Print Bill
            </button>
            """,
            height=50,
        )
    with col2:
        st.download_button(
            "📥 Download Bill",
            data=_build_receipt_text(bill),
            file_name=f"{bill['invoice_number']}.txt",
            mime="text/plain",
            use_container_width=True,
        )


def _format_datetime(iso_string: str) -> str:
    from datetime import datetime
    try:
        return datetime.fromisoformat(iso_string).strftime("%d %b %Y, %I:%M %p")
    except ValueError:
        return iso_string


def _build_receipt_text(bill: dict) -> str:
    lines = [
        config.APP_NAME,
        config.APP_TAGLINE,
        "-" * 40,
        f"Invoice #: {bill['invoice_number']}",
        f"Date/Time: {_format_datetime(bill['bill_date'])}",
        f"Customer: {bill['customer_name']} ({bill['customer_phone'] or '-'})",
        "-" * 40,
    ]
    for item in bill["items"]:
        lines.append(
            f"{item['product_name']:<20} Qty:{item['quantity']:<4} "
            f"{config.CURRENCY_SYMBOL}{item['unit_price']:<8.2f} "
            f"GST:{config.CURRENCY_SYMBOL}{item['gst_amount']:<7.2f} "
            f"= {config.CURRENCY_SYMBOL}{item['line_total']:.2f}"
        )
    lines += [
        "-" * 40,
        f"Subtotal: {config.CURRENCY_SYMBOL}{bill['subtotal']:.2f}",
        f"Discount: -{config.CURRENCY_SYMBOL}{bill['discount']:.2f}",
        f"GST: {config.CURRENCY_SYMBOL}{bill['gst_amount']:.2f}",
        f"Grand Total: {config.CURRENCY_SYMBOL}{bill['grand_total']:.2f}",
        f"Payment Method: {bill['payment_method']}",
        "-" * 40,
        "Thank You for Shopping with MARTIQ! <3",
        "We value your shopping.",
        "Visit MARTIQ Again!",
        "Have a wonderful day! :)",
    ]
    return "\n".join(lines)
