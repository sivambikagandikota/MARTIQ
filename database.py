"""
MARTIQ - Database Layer
------------------------
Every SQL statement in the whole application lives here (or will,
as we add more views in later phases). Views never write raw SQL
directly - they call functions from this file. This keeps the app
easy to explain: "all data logic is in one file".
"""

import sqlite3
import hashlib
import os
from datetime import datetime

import config


# ==================================================================
# CONNECTION HELPERS
# ==================================================================

def get_connection():
    """Return a SQLite connection with foreign keys enabled and
    rows accessible by column name (like a dictionary)."""
    os.makedirs(config.DATABASE_DIR, exist_ok=True)
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(plain_text_password: str) -> str:
    """Simple, dependency-free password hashing using SHA-256."""
    return hashlib.sha256(plain_text_password.encode("utf-8")).hexdigest()


# ==================================================================
# SCHEMA CREATION
# ==================================================================

def init_db():
    """
    Create every table if it does not already exist, then make sure
    a demo admin account exists. Safe to call every time the app
    starts - it will never wipe existing data.
    """
    conn = get_connection()
    cur = conn.cursor()

    # -------------------- users --------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            full_name     TEXT NOT NULL DEFAULT 'Administrator',
            role          TEXT NOT NULL DEFAULT 'Admin',
            created_at    TEXT NOT NULL
        )
    """)

    # -------------------- customers --------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            customer_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT NOT NULL,
            phone         TEXT NOT NULL UNIQUE,
            email         TEXT,
            address       TEXT,
            membership    TEXT NOT NULL DEFAULT 'Regular'
                          CHECK (membership IN ('Regular','Silver','Gold','Platinum')),
            credit_limit  REAL NOT NULL DEFAULT 0 CHECK (credit_limit >= 0),
            used_credit   REAL NOT NULL DEFAULT 0 CHECK (used_credit >= 0),
            status        TEXT NOT NULL DEFAULT 'Active'
                          CHECK (status IN ('Active','Inactive')),
            created_at    TEXT NOT NULL
        )
    """)

    # -------------------- products --------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            product_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            name           TEXT NOT NULL,
            category       TEXT NOT NULL DEFAULT 'General',
            price          REAL NOT NULL CHECK (price >= 0),
            stock          INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
            min_stock      INTEGER NOT NULL DEFAULT 5 CHECK (min_stock >= 0),
            gst_percent    REAL NOT NULL DEFAULT 5.0 CHECK (gst_percent >= 0),
            supplier       TEXT,
            status         TEXT NOT NULL DEFAULT 'Active'
                           CHECK (status IN ('Active','Discontinued')),
            created_at     TEXT NOT NULL
        )
    """)

    # -------------------- schema migrations --------------------
    # Barcode support was added after the initial database version.
    # Keep this migration safe so existing databases continue to work.
    try:
        cur.execute("ALTER TABLE products ADD COLUMN barcode TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_products_barcode ON products(barcode) WHERE barcode IS NOT NULL AND barcode <> ''")
    conn.commit()

    # -------------------- bills --------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bills (
            bill_id         INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_number  TEXT NOT NULL UNIQUE,
            customer_id     INTEGER NOT NULL,
            bill_date       TEXT NOT NULL,
            subtotal        REAL NOT NULL DEFAULT 0,
            discount        REAL NOT NULL DEFAULT 0,
            gst_amount      REAL NOT NULL DEFAULT 0,
            grand_total     REAL NOT NULL DEFAULT 0,
            payment_method  TEXT NOT NULL
                            CHECK (payment_method IN ('Cash','UPI','Debit Card','Credit')),
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        )
    """)

    # -------------------- bill_items --------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bill_items (
            item_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_id     INTEGER NOT NULL,
            product_id  INTEGER NOT NULL,
            quantity    INTEGER NOT NULL CHECK (quantity > 0),
            unit_price  REAL NOT NULL CHECK (unit_price >= 0),
            gst_amount  REAL NOT NULL DEFAULT 0,
            line_total  REAL NOT NULL DEFAULT 0,
            FOREIGN KEY (bill_id) REFERENCES bills(bill_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        )
    """)

    # -------------------- payments --------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            payment_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_id         INTEGER NOT NULL,
            payment_method  TEXT NOT NULL,
            amount          REAL NOT NULL CHECK (amount >= 0),
            payment_date    TEXT NOT NULL,
            status          TEXT NOT NULL DEFAULT 'Completed',
            FOREIGN KEY (bill_id) REFERENCES bills(bill_id)
        )
    """)

    conn.commit()

    # -------------------- seed demo admin user --------------------
    cur.execute("SELECT COUNT(*) AS cnt FROM users WHERE username = ?", (config.DEMO_USERNAME,))
    if cur.fetchone()["cnt"] == 0:
        cur.execute(
            "INSERT INTO users (username, password_hash, full_name, role, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                config.DEMO_USERNAME,
                hash_password(config.DEMO_PASSWORD),
                "MARTIQ Administrator",
                "Admin",
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        conn.commit()

    # -------------------- seed walk-in customer --------------------
    # Used by Billing when no registered customer is selected.
    # bills.customer_id is NOT NULL, so this placeholder avoids a
    # schema change while still supporting walk-in sales.
    cur.execute("SELECT COUNT(*) AS cnt FROM customers WHERE phone = ?", (config.WALKIN_CUSTOMER_PHONE,))
    if cur.fetchone()["cnt"] == 0:
        cur.execute(
            """
            INSERT INTO customers
                (name, phone, email, address, membership, credit_limit, used_credit, status, created_at)
            VALUES (?, ?, NULL, NULL, 'Regular', 0, 0, 'Active', ?)
            """,
            (config.WALKIN_CUSTOMER_NAME, config.WALKIN_CUSTOMER_PHONE, datetime.now().isoformat(timespec="seconds")),
        )
        conn.commit()

    conn.close()


# ==================================================================
# PHASE 1 HELPER: quick status check used by app.py to prove the
# database was created correctly (used only for testing right now,
# real dashboard queries come in Phase 3).
# ==================================================================

def get_table_counts():
    """Return a dict of {table_name: row_count} for every core table."""
    conn = get_connection()
    cur = conn.cursor()
    tables = ["users", "customers", "products", "bills", "bill_items", "payments"]
    counts = {}
    for t in tables:
        cur.execute(f"SELECT COUNT(*) AS cnt FROM {t}")
        counts[t] = cur.fetchone()["cnt"]
    conn.close()
    return counts


def verify_user(username: str, password: str) -> bool:
    """Check a username/password pair against the users table."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    if row is None:
        return False
    return row["password_hash"] == hash_password(password)


# ==================================================================
# PHASE 3: DASHBOARD QUERIES
# ------------------------------------------------------------------
# Every value on the Dashboard comes from a live query in this
# section. Nothing here is hard-coded. All queries are written to
# return safe defaults (0, empty list) when tables are empty, since
# Billing/Customers/Products are not built yet as of Phase 3.
# ==================================================================

def get_dashboard_stats():
    """
    Core KPI numbers for the top of the Dashboard:
    total sales, total bills, average bill value, items sold,
    total customers, total products.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            COALESCE(SUM(grand_total), 0) AS total_sales,
            COUNT(*)                      AS total_bills,
            COALESCE(AVG(grand_total), 0) AS avg_bill_value
        FROM bills
    """)
    bill_row = cur.fetchone()

    cur.execute("SELECT COALESCE(SUM(quantity), 0) AS items_sold FROM bill_items")
    items_row = cur.fetchone()

    cur.execute("SELECT COUNT(*) AS total_customers FROM customers")
    customer_row = cur.fetchone()

    cur.execute("SELECT COUNT(*) AS total_products FROM products")
    product_row = cur.fetchone()

    conn.close()

    return {
        "total_sales": bill_row["total_sales"],
        "total_bills": bill_row["total_bills"],
        "avg_bill_value": bill_row["avg_bill_value"],
        "items_sold": items_row["items_sold"],
        "total_customers": customer_row["total_customers"],
        "total_products": product_row["total_products"],
    }


def get_low_stock_products(limit: int = 8):
    """Active products with 0 < stock <= min_stock, lowest stock first."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT product_id, name, category, stock, min_stock
        FROM products
        WHERE status = 'Active' AND stock > 0 AND stock <= min_stock
        ORDER BY stock ASC
        LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_out_of_stock_products(limit: int = 8):
    """Active products with stock == 0."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT product_id, name, category, stock, min_stock
        FROM products
        WHERE status = 'Active' AND stock = 0
        ORDER BY name ASC
        LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_credit_alerts(limit: int = 8, threshold_percent: float = 80.0):
    """
    Active customers who have used threshold_percent or more of their
    credit limit. Percentage is computed in Python to safely avoid
    divide-by-zero for customers with no credit limit set.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT customer_id, name, phone, credit_limit, used_credit
        FROM customers
        WHERE status = 'Active' AND credit_limit > 0
    """)
    rows = cur.fetchall()
    conn.close()

    alerts = []
    for r in rows:
        limit_val = r["credit_limit"]
        used = r["used_credit"]
        usage_pct = (used / limit_val * 100) if limit_val > 0 else 0
        if usage_pct >= threshold_percent:
            alerts.append({
                "customer_id": r["customer_id"],
                "name": r["name"],
                "phone": r["phone"],
                "credit_limit": limit_val,
                "used_credit": used,
                "available_credit": limit_val - used,
                "usage_pct": usage_pct,
            })

    alerts.sort(key=lambda a: a["usage_pct"], reverse=True)
    return alerts[:limit]


def get_recent_transactions(limit: int = 8):
    """Most recent bills with the customer name attached."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT b.bill_id, b.invoice_number, b.bill_date, b.grand_total,
               b.payment_method, c.name AS customer_name
        FROM bills b
        LEFT JOIN customers c ON b.customer_id = c.customer_id
        ORDER BY b.bill_date DESC, b.bill_id DESC
        LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_daily_sales_trend(days: int = 14):
    """
    Total sales per calendar day for the last `days` days, ending
    today. Days with no sales are included with a total of 0 so the
    chart doesn't show misleading gaps.
    """
    from datetime import date, timedelta

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT date(bill_date) AS day, SUM(grand_total) AS total
        FROM bills
        WHERE date(bill_date) >= date('now', ?)
        GROUP BY day
    """, (f"-{days - 1} days",))
    totals_by_day = {r["day"]: r["total"] for r in cur.fetchall()}
    conn.close()

    today = date.today()
    result = []
    for i in range(days - 1, -1, -1):
        day = today - timedelta(days=i)
        day_str = day.isoformat()
        result.append((day_str, totals_by_day.get(day_str, 0) or 0))
    return result


def get_monthly_sales_trend(months: int = 6):
    """
    Total sales per calendar month for the last `months` months,
    ending with the current month. Months with no sales show 0.
    """
    from datetime import date

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT strftime('%Y-%m', bill_date) AS month, SUM(grand_total) AS total
        FROM bills
        GROUP BY month
    """)
    totals_by_month = {r["month"]: r["total"] for r in cur.fetchall()}
    conn.close()

    today = date.today()
    months_list = []
    y, m = today.year, today.month
    for _ in range(months):
        months_list.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    months_list.reverse()

    return [(month, totals_by_month.get(month, 0) or 0) for month in months_list]


# ==================================================================
# PHASE 4: CUSTOMER MANAGEMENT
# ------------------------------------------------------------------
# All Customer CRUD logic. Reuses the existing `customers` table
# from Phase 1 - no schema changes. All queries are parameterized.
# ==================================================================

def bulk_import_customers(df):
    required=["Name","Phone"]
    missing=[c for c in required if c not in df.columns]
    if missing: return {"success":0,"failed":len(df),"duplicates":0,"errors":[f"Missing columns: {', '.join(missing)}"]}
    conn=get_connection(); cur=conn.cursor(); success=failed=duplicates=0; errors=[]
    try:
        for idx,row in df.iterrows():
            try:
                name=str(row.get("Name","")).strip(); phone=str(row.get("Phone","")).strip()
                if not name or not phone: raise ValueError("Name and Phone are required")
                email=str(row.get("Email","") or "").strip(); address=str(row.get("Address","") or "").strip(); membership=str(row.get("Membership","Regular") or "Regular").strip(); credit=float(row.get("Credit Limit",0) or 0)
                if credit < 0: raise ValueError("Credit Limit cannot be negative")
                cur.execute("SELECT customer_id FROM customers WHERE phone=?",(phone,))
                if cur.fetchone(): duplicates+=1; continue
                cur.execute("""INSERT INTO customers(name,phone,email,address,membership,credit_limit,used_credit,status,created_at) VALUES(?,?,?,?,?,?,0,'Active',?)""",(name,phone,email,address,membership,credit,datetime.now().isoformat(timespec="seconds")))
                success+=1
            except Exception as e:
                failed+=1; errors.append(f"Row {idx+2}: {e}")
        conn.commit(); conn.close(); return {"success":success,"failed":failed,"duplicates":duplicates,"errors":errors[:50]}
    except Exception as e:
        conn.rollback(); conn.close(); return {"success":0,"failed":len(df),"duplicates":0,"errors":[str(e)]}


def get_customer_stats():
    """Total customers and active customers, for the summary cards."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            COUNT(*) AS total,
            COALESCE(SUM(CASE WHEN status = 'Active' THEN 1 ELSE 0 END), 0) AS active
        FROM customers
    """)
    row = cur.fetchone()
    conn.close()
    return {"total_customers": row["total"], "active_customers": row["active"]}


def get_all_customers(search: str = "", membership_filter: str = "All", status_filter: str = "All"):
    """
    Return customers matching an optional search term (ID/name/phone)
    and optional membership/status filters. Each row also includes a
    computed `available_credit` field.
    """
    conn = get_connection()
    cur = conn.cursor()

    query = "SELECT * FROM customers WHERE 1=1"
    params = []

    search = (search or "").strip()
    if search:
        query += " AND (CAST(customer_id AS TEXT) LIKE ? OR name LIKE ? OR phone LIKE ?)"
        like_term = f"%{search}%"
        params += [like_term, like_term, like_term]

    if membership_filter and membership_filter != "All":
        query += " AND membership = ?"
        params.append(membership_filter)

    if status_filter and status_filter != "All":
        query += " AND status = ?"
        params.append(status_filter)

    query += " ORDER BY customer_id DESC"

    cur.execute(query, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()

    for r in rows:
        r["available_credit"] = r["credit_limit"] - r["used_credit"]
    return rows


def get_customer_by_id(customer_id: int):
    """Fetch a single customer by ID, or None if not found."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM customers WHERE customer_id = ?", (customer_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def add_customer(name: str, phone: str, email: str, address: str, membership: str, credit_limit: float):
    """
    Insert a new customer. Returns (success: bool, result) where
    result is the new customer_id on success or a friendly error
    message on failure. Duplicate phone numbers are rejected safely
    (relies on the existing UNIQUE constraint on phone).
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO customers
                (name, phone, email, address, membership, credit_limit, used_credit, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 0, 'Active', ?)
            """,
            (name, phone, email, address, membership, credit_limit, datetime.now().isoformat(timespec="seconds")),
        )
        conn.commit()
        new_id = cur.lastrowid
        conn.close()
        return True, new_id
    except sqlite3.IntegrityError:
        conn.close()
        return False, "A customer with this phone number already exists."
    except sqlite3.Error as e:
        conn.close()
        return False, f"Database error while adding customer: {e}"


def update_customer(customer_id: int, name: str, phone: str, email: str, address: str,
                     membership: str, credit_limit: float, status: str):
    """Update an existing customer's details. Returns (success, message)."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            UPDATE customers
            SET name = ?, phone = ?, email = ?, address = ?,
                membership = ?, credit_limit = ?, status = ?
            WHERE customer_id = ?
            """,
            (name, phone, email, address, membership, credit_limit, status, customer_id),
        )
        conn.commit()
        conn.close()
        return True, "Customer updated successfully."
    except sqlite3.IntegrityError:
        conn.close()
        return False, "Another customer already uses this phone number."
    except sqlite3.Error as e:
        conn.close()
        return False, f"Database error while updating customer: {e}"


def customer_bill_count(customer_id: int) -> int:
    """How many bills reference this customer (used to guard deletion)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS cnt FROM bills WHERE customer_id = ?", (customer_id,))
    count = cur.fetchone()["cnt"]
    conn.close()
    return count


def delete_customer(customer_id: int):
    """
    Delete a customer, but only if no bills reference them - this
    protects the bills.customer_id foreign key from being orphaned.
    Returns (success, message).
    """
    existing_bills = customer_bill_count(customer_id)
    if existing_bills > 0:
        return False, (
            f"Cannot delete this customer — they have {existing_bills} bill(s) on record. "
            f"Set their status to Inactive instead if they should no longer be billed."
        )

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM customers WHERE customer_id = ?", (customer_id,))
        conn.commit()
        conn.close()
        return True, "Customer deleted successfully."
    except sqlite3.Error as e:
        conn.close()
        return False, f"Database error while deleting customer: {e}"


def get_walkin_customer_id() -> int:
    """Return the customer_id of the seeded Walk-in Customer row."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT customer_id FROM customers WHERE phone = ?", (config.WALKIN_CUSTOMER_PHONE,))
    row = cur.fetchone()
    conn.close()
    return row["customer_id"] if row else None


def get_billable_customers():
    """
    All active customers for the Billing dropdown, Walk-in Customer
    listed first for convenience.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT customer_id, name, phone, credit_limit, used_credit
        FROM customers
        WHERE status = 'Active'
        ORDER BY (phone = ?) DESC, name ASC
    """, (config.WALKIN_CUSTOMER_PHONE,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


# ==================================================================
# PRODUCT & INVENTORY MANAGEMENT
# ------------------------------------------------------------------
# Full CRUD for the `products` table (created in Phase 1). No
# schema changes - all fields already existed.
# ==================================================================

def get_product_stats():
    """Summary counts for the top of the Products page."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            COUNT(*) AS total,
            COALESCE(SUM(CASE WHEN status = 'Active' AND stock = 0 THEN 1 ELSE 0 END), 0) AS out_of_stock,
            COALESCE(SUM(CASE WHEN status = 'Active' AND stock > 0 AND stock <= min_stock THEN 1 ELSE 0 END), 0) AS low_stock,
            COALESCE(SUM(CASE WHEN status = 'Active' AND stock > min_stock THEN 1 ELSE 0 END), 0) AS healthy
        FROM products
    """)
    row = cur.fetchone()
    conn.close()
    return {
        "total_products": row["total"],
        "out_of_stock": row["out_of_stock"],
        "low_stock": row["low_stock"],
        "healthy_stock": row["healthy"],
    }


def get_categories():
    """Distinct product categories currently in use, for filter dropdowns."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT category FROM products ORDER BY category ASC")
    cats = [r["category"] for r in cur.fetchall()]
    conn.close()
    return cats


def get_all_products(search: str = "", category_filter: str = "All", status_filter: str = "All"):
    """Products matching an optional search (ID/name) and filters."""
    conn = get_connection()
    cur = conn.cursor()

    query = "SELECT * FROM products WHERE 1=1"
    params = []

    search = (search or "").strip()
    if search:
        query += " AND (CAST(product_id AS TEXT) LIKE ? OR name LIKE ?)"
        like_term = f"%{search}%"
        params += [like_term, like_term]

    if category_filter and category_filter != "All":
        query += " AND category = ?"
        params.append(category_filter)

    if status_filter and status_filter != "All":
        query += " AND status = ?"
        params.append(status_filter)

    query += " ORDER BY product_id DESC"

    cur.execute(query, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()

    for r in rows:
        if r["stock"] == 0:
            r["stock_status"] = "🔴 Out of Stock"
        elif r["stock"] <= r["min_stock"]:
            r["stock_status"] = "🟡 Low Stock"
        else:
            r["stock_status"] = "🟢 In Stock"
    return rows


def get_product_by_id(product_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products WHERE product_id = ?", (product_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def add_product(name: str, category: str, price: float, stock: int, min_stock: int,
                 gst_percent: float, supplier: str, barcode: str = ""):
    """Insert a product. A blank barcode is automatically assigned after insert."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        barcode = (barcode or "").strip() or None
        cur.execute(
            """
            INSERT INTO products
                (name, category, price, stock, min_stock, gst_percent, supplier, status, created_at, barcode)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'Active', ?, ?)
            """,
            (name, category, price, stock, min_stock, gst_percent, supplier,
             datetime.now().isoformat(timespec="seconds"), barcode),
        )
        new_id = cur.lastrowid
        if not barcode:
            generated = f"MARTIQ{new_id:08d}"
            cur.execute("UPDATE products SET barcode = ? WHERE product_id = ?", (generated, new_id))
            barcode = generated
        conn.commit()
        conn.close()
        return True, new_id
    except sqlite3.IntegrityError as e:
        conn.rollback(); conn.close()
        return False, f"Could not add product — duplicate/invalid data ({e})."
    except sqlite3.Error as e:
        conn.rollback(); conn.close()
        return False, f"Database error while adding product: {e}"


def get_product_by_barcode(barcode: str):
    barcode = (barcode or "").strip()
    if not barcode:
        return None
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT * FROM products WHERE barcode = ? AND status = 'Active'", (barcode,))
    row = cur.fetchone(); conn.close()
    return dict(row) if row else None


def update_product(product_id: int, name: str, category: str, price: float, stock: int,
                    min_stock: int, gst_percent: float, supplier: str, status: str, barcode: str = ""):
    """Update an existing product. Returns (success, message)."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            UPDATE products
            SET name = ?, category = ?, price = ?, stock = ?, min_stock = ?,
                gst_percent = ?, supplier = ?, status = ?, barcode = ?
            WHERE product_id = ?
            """,
            (name, category, price, stock, min_stock, gst_percent, supplier, status, barcode.strip() or None, product_id),
        )
        conn.commit()
        conn.close()
        return True, "Product updated successfully."
    except sqlite3.IntegrityError as e:
        conn.close()
        return False, f"Could not update product — invalid data ({e})."
    except sqlite3.Error as e:
        conn.close()
        return False, f"Database error while updating product: {e}"


def bulk_import_products(df):
    """Validate and import product rows into the existing products table."""
    required = ["Product Name", "Category", "Price", "Opening Stock", "Minimum Stock Level", "GST %"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        return {"success": 0, "failed": len(df), "duplicates": 0, "errors": [f"Missing columns: {', '.join(missing)}"]}
    conn = get_connection(); cur = conn.cursor()
    success = failed = duplicates = 0; errors=[]
    try:
        for idx, row in df.iterrows():
            try:
                name=str(row.get("Product Name", "")).strip(); category=str(row.get("Category", "")).strip()
                if not name or not category: raise ValueError("Product Name and Category are required")
                price=float(row.get("Price", 0)); stock=int(float(row.get("Opening Stock", 0))); min_stock=int(float(row.get("Minimum Stock Level", 0))); gst=float(row.get("GST %", 5))
                supplier=str(row.get("Supplier", "") or "").strip(); barcode=str(row.get("Barcode", "") or "").strip() or None
                if price < 0 or stock < 0 or min_stock < 0 or gst < 0: raise ValueError("Price/stock/GST cannot be negative")
                if barcode:
                    cur.execute("SELECT product_id FROM products WHERE barcode = ?", (barcode,))
                    if cur.fetchone(): duplicates += 1; continue
                cur.execute("SELECT product_id FROM products WHERE lower(name)=lower(?)", (name,))
                if cur.fetchone(): duplicates += 1; continue
                cur.execute("""INSERT INTO products(name,category,price,stock,min_stock,gst_percent,supplier,status,created_at,barcode) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                    (name,category,price,stock,min_stock,gst,supplier,"Active",datetime.now().isoformat(timespec="seconds"),barcode))
                new_id=cur.lastrowid
                if not barcode: cur.execute("UPDATE products SET barcode=? WHERE product_id=?", (f"MARTIQ{new_id:08d}",new_id))
                success += 1
            except Exception as e:
                failed += 1; errors.append(f"Row {idx+2}: {e}")
        conn.commit(); conn.close()
        return {"success":success,"failed":failed,"duplicates":duplicates,"errors":errors[:50]}
    except Exception as e:
        conn.rollback(); conn.close(); return {"success":0,"failed":len(df),"duplicates":0,"errors":[str(e)]}


def product_bill_item_count(product_id: int) -> int:
    """How many bill_items reference this product (used to guard deletion)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS cnt FROM bill_items WHERE product_id = ?", (product_id,))
    count = cur.fetchone()["cnt"]
    conn.close()
    return count


def delete_product(product_id: int):
    """
    Delete a product, but only if it has never appeared on a bill -
    this protects bill_items.product_id from being orphaned.
    Returns (success, message).
    """
    existing = product_bill_item_count(product_id)
    if existing > 0:
        return False, (
            f"Cannot delete this product — it appears on {existing} past bill line item(s). "
            f"Set its status to Discontinued instead."
        )

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM products WHERE product_id = ?", (product_id,))
        conn.commit()
        conn.close()
        return True, "Product deleted successfully."
    except sqlite3.Error as e:
        conn.close()
        return False, f"Database error while deleting product: {e}"


# ==================================================================
# BILLING / POS
# ------------------------------------------------------------------
# Creates bills atomically: one bill row, one bill_items row per
# cart line, a stock decrement per product, a customer credit
# update when paid on Credit, and one payments row. All of this
# happens on a single connection so it either all succeeds or all
# rolls back together.
# ==================================================================

def generate_invoice_number() -> str:
    """INV-YYYYMMDD-#### , unique per day, sequential."""
    conn = get_connection()
    cur = conn.cursor()
    today_str = datetime.now().strftime("%Y%m%d")
    cur.execute(
        "SELECT COUNT(*) AS cnt FROM bills WHERE invoice_number LIKE ?",
        (f"INV-{today_str}-%",),
    )
    count_today = cur.fetchone()["cnt"]
    conn.close()
    return f"INV-{today_str}-{count_today + 1:04d}"


def create_bill(customer_id: int, cart_items: list, discount: float, payment_method: str):
    """
    cart_items: list of dicts, each with product_id, name, unit_price,
    gst_percent, quantity.

    Validates stock and (for Credit) available credit BEFORE writing
    anything. Returns (success, result) where result is a dict with
    bill_id/invoice_number/totals on success, or an error string on
    failure.
    """
    if not cart_items:
        return False, "Cart is empty — add at least one product before billing."

    conn = get_connection()
    cur = conn.cursor()
    try:
        # -------- re-check stock for every item under the same connection --------
        for item in cart_items:
            cur.execute("SELECT stock, name FROM products WHERE product_id = ?", (item["product_id"],))
            row = cur.fetchone()
            if row is None:
                conn.close()
                return False, f"Product '{item['name']}' no longer exists."
            if row["stock"] < item["quantity"]:
                conn.close()
                return False, (
                    f"Insufficient stock for '{row['name']}' — only {row['stock']} available, "
                    f"{item['quantity']} requested."
                )

        # -------- compute totals --------
        subtotal = sum(i["unit_price"] * i["quantity"] for i in cart_items)
        gst_amount = sum(i["unit_price"] * i["quantity"] * (i["gst_percent"] / 100.0) for i in cart_items)
        discount = max(0.0, float(discount))
        grand_total = round(subtotal - discount + gst_amount, 2)
        if grand_total < 0:
            conn.close()
            return False, "Discount cannot exceed the subtotal + GST."

        # -------- credit limit check (before any writes) --------
        if payment_method == "Credit":
            cur.execute("SELECT credit_limit, used_credit, name FROM customers WHERE customer_id = ?", (customer_id,))
            cust = cur.fetchone()
            if cust is None:
                conn.close()
                return False, "Selected customer not found."
            available_credit = cust["credit_limit"] - cust["used_credit"]
            if grand_total > available_credit:
                conn.close()
                return False, (
                    f"Credit limit exceeded for {cust['name']}. Available credit: "
                    f"{config.CURRENCY_SYMBOL}{available_credit:,.2f}, bill total: "
                    f"{config.CURRENCY_SYMBOL}{grand_total:,.2f}."
                )

        # -------- insert bill --------
        invoice_number = generate_invoice_number()
        bill_date = datetime.now().isoformat(timespec="seconds")
        cur.execute(
            """
            INSERT INTO bills
                (invoice_number, customer_id, bill_date, subtotal, discount, gst_amount, grand_total, payment_method)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (invoice_number, customer_id, bill_date, round(subtotal, 2), discount,
             round(gst_amount, 2), grand_total, payment_method),
        )
        bill_id = cur.lastrowid

        # -------- insert bill items + decrement stock --------
        for item in cart_items:
            line_subtotal = item["unit_price"] * item["quantity"]
            line_gst = line_subtotal * (item["gst_percent"] / 100.0)
            line_total = round(line_subtotal + line_gst, 2)

            cur.execute(
                """
                INSERT INTO bill_items (bill_id, product_id, quantity, unit_price, gst_amount, line_total)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (bill_id, item["product_id"], item["quantity"], item["unit_price"], round(line_gst, 2), line_total),
            )

            cur.execute(
                "UPDATE products SET stock = stock - ? WHERE product_id = ? AND stock >= ?",
                (item["quantity"], item["product_id"], item["quantity"]),
            )
            if cur.rowcount == 0:
                raise sqlite3.Error(f"Stock update failed for product_id {item['product_id']} (race condition).")

        # -------- update customer credit if paid on Credit --------
        if payment_method == "Credit":
            cur.execute(
                "UPDATE customers SET used_credit = used_credit + ? WHERE customer_id = ?",
                (grand_total, customer_id),
            )

        # -------- record payment --------
        cur.execute(
            """
            INSERT INTO payments (bill_id, payment_method, amount, payment_date, status)
            VALUES (?, ?, ?, ?, 'Completed')
            """,
            (bill_id, payment_method, grand_total, bill_date),
        )

        conn.commit()
        conn.close()

        return True, {
            "bill_id": bill_id,
            "invoice_number": invoice_number,
            "bill_date": bill_date,
            "subtotal": round(subtotal, 2),
            "discount": discount,
            "gst_amount": round(gst_amount, 2),
            "grand_total": grand_total,
            "payment_method": payment_method,
        }

    except sqlite3.Error as e:
        conn.rollback()
        conn.close()
        return False, f"Database error while creating the bill: {e}"


def get_bill_details(bill_id: int):
    """Full bill header + customer info + line items, for the receipt/reprint."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT b.*, c.name AS customer_name, c.phone AS customer_phone
        FROM bills b
        LEFT JOIN customers c ON b.customer_id = c.customer_id
        WHERE b.bill_id = ?
    """, (bill_id,))
    bill_row = cur.fetchone()
    if bill_row is None:
        conn.close()
        return None

    cur.execute("""
        SELECT bi.*, p.name AS product_name
        FROM bill_items bi
        LEFT JOIN products p ON bi.product_id = p.product_id
        WHERE bi.bill_id = ?
    """, (bill_id,))
    items = [dict(r) for r in cur.fetchall()]

    conn.close()
    bill = dict(bill_row)
    bill["items"] = items
    return bill


# ==================================================================
# ANALYTICS
# ------------------------------------------------------------------
# All queries accept an optional date range (inclusive, 'YYYY-MM-DD'
# strings) and return empty results gracefully when there is no data.
# ==================================================================

def _date_filter_clause(start_date, end_date, column="b.bill_date"):
    """Build a WHERE clause fragment + params for an optional date range."""
    clauses, params = [], []
    if start_date:
        clauses.append(f"date({column}) >= date(?)")
        params.append(start_date)
    if end_date:
        clauses.append(f"date({column}) <= date(?)")
        params.append(end_date)
    return clauses, params


def get_sales_over_time(start_date=None, end_date=None):
    """Daily sales totals within an optional date range."""
    conn = get_connection()
    cur = conn.cursor()
    clauses, params = _date_filter_clause(start_date, end_date)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    cur.execute(f"""
        SELECT date(bill_date) AS day, SUM(grand_total) AS total
        FROM bills b
        {where}
        GROUP BY day
        ORDER BY day ASC
    """, params)
    rows = [(r["day"], r["total"] or 0) for r in cur.fetchall()]
    conn.close()
    return rows


def get_top_selling_products(limit=10, start_date=None, end_date=None, category=None):
    conn = get_connection()
    cur = conn.cursor()
    clauses, params = _date_filter_clause(start_date, end_date)
    query = """
        SELECT p.product_id, p.name, p.category,
               SUM(bi.quantity) AS total_qty,
               SUM(bi.line_total) AS total_revenue
        FROM bill_items bi
        JOIN bills b ON bi.bill_id = b.bill_id
        JOIN products p ON bi.product_id = p.product_id
    """
    if category and category != "All":
        clauses.append("p.category = ?")
        params.append(category)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " GROUP BY p.product_id ORDER BY total_qty DESC LIMIT ?"
    params.append(limit)

    cur.execute(query, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_category_sales(start_date=None, end_date=None):
    conn = get_connection()
    cur = conn.cursor()
    clauses, params = _date_filter_clause(start_date, end_date)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    cur.execute(f"""
        SELECT p.category, SUM(bi.line_total) AS total_revenue
        FROM bill_items bi
        JOIN bills b ON bi.bill_id = b.bill_id
        JOIN products p ON bi.product_id = p.product_id
        {where}
        GROUP BY p.category
        ORDER BY total_revenue DESC
    """, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_payment_method_distribution(start_date=None, end_date=None):
    conn = get_connection()
    cur = conn.cursor()
    clauses, params = _date_filter_clause(start_date, end_date)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    cur.execute(f"""
        SELECT payment_method, COUNT(*) AS bill_count, SUM(grand_total) AS total
        FROM bills b
        {where}
        GROUP BY payment_method
        ORDER BY total DESC
    """, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_top_customers(limit=10, start_date=None, end_date=None):
    conn = get_connection()
    cur = conn.cursor()
    clauses, params = _date_filter_clause(start_date, end_date)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    cur.execute(f"""
        SELECT c.customer_id, c.name, COUNT(b.bill_id) AS bill_count, SUM(b.grand_total) AS total_spent
        FROM bills b
        JOIN customers c ON b.customer_id = c.customer_id
        {where}
        GROUP BY c.customer_id
        ORDER BY total_spent DESC
        LIMIT ?
    """, params + [limit])
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_bill_value_list(start_date=None, end_date=None):
    """Raw list of grand_total values within range, for a distribution histogram."""
    conn = get_connection()
    cur = conn.cursor()
    clauses, params = _date_filter_clause(start_date, end_date)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    cur.execute(f"SELECT grand_total FROM bills b {where}", params)
    values = [r["grand_total"] for r in cur.fetchall()]
    conn.close()
    return values


def get_stock_overview():
    """Current-state counts for a stock overview chart (not date-filtered)."""
    stats = get_product_stats()
    return {
        "In Stock": stats["healthy_stock"],
        "Low Stock": stats["low_stock"],
        "Out of Stock": stats["out_of_stock"],
    }


# ==================================================================
# REPORTS
# ------------------------------------------------------------------
# Mostly thin wrappers/joins for exportable tabular reports.
# ==================================================================

def get_sales_report(start_date=None, end_date=None, payment_method="All", customer_id=None):
    conn = get_connection()
    cur = conn.cursor()
    clauses, params = _date_filter_clause(start_date, end_date)
    if payment_method and payment_method != "All":
        clauses.append("b.payment_method = ?")
        params.append(payment_method)
    if customer_id:
        clauses.append("b.customer_id = ?")
        params.append(customer_id)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    cur.execute(f"""
        SELECT b.invoice_number, b.bill_date, c.name AS customer_name,
               b.subtotal, b.discount, b.gst_amount, b.grand_total, b.payment_method
        FROM bills b
        LEFT JOIN customers c ON b.customer_id = c.customer_id
        {where}
        ORDER BY b.bill_date DESC
    """, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_billing_report(start_date=None, end_date=None):
    """Line-item level detail: every product sold on every bill."""
    conn = get_connection()
    cur = conn.cursor()
    clauses, params = _date_filter_clause(start_date, end_date)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    cur.execute(f"""
        SELECT b.invoice_number, b.bill_date, c.name AS customer_name,
               p.name AS product_name, bi.quantity, bi.unit_price, bi.gst_amount, bi.line_total,
               b.payment_method
        FROM bill_items bi
        JOIN bills b ON bi.bill_id = b.bill_id
        LEFT JOIN customers c ON b.customer_id = c.customer_id
        LEFT JOIN products p ON bi.product_id = p.product_id
        {where}
        ORDER BY b.bill_date DESC
    """, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_inventory_report():
    """Current stock snapshot with computed status, for the Inventory Report."""
    return get_all_products()


def get_customer_report():
    """Full customer list with computed available credit, for the Customer Report."""
    return get_all_customers()


# ==================================================================
# SMART INVENTORY (rule-based, not machine learning)
# ------------------------------------------------------------------
# "Smart Inventory Recommendations" = a small set of explainable
# rules over current stock + recent sales velocity. No ML model is
# used or implied anywhere in this section.
# ==================================================================

def get_product_sales_velocity(days: int = 30):
    """
    dict of product_id -> quantity sold in the last `days` days.
    Products with no sales in the window are simply absent (caller
    treats missing as 0).
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT bi.product_id, SUM(bi.quantity) AS qty
        FROM bill_items bi
        JOIN bills b ON bi.bill_id = b.bill_id
        WHERE date(b.bill_date) >= date('now', ?)
        GROUP BY bi.product_id
    """, (f"-{days} days",))
    result = {r["product_id"]: r["qty"] for r in cur.fetchall()}
    conn.close()
    return result


def get_smart_inventory_table(days: int = 30):
    """
    One row per active product with:
      - recent_sales: units sold in the last `days` days
      - avg_daily_sales: recent_sales / days
      - days_of_stock_left: stock / avg_daily_sales (None if no sales)
      - status: Out of Stock / Low Stock / Reorder Soon / Healthy
      - recommended_reorder: suggested units to order
      - reason: plain-English explanation (for the viva)

    Rule set (fully explainable, no ML):
      1. stock == 0                          -> Out of Stock
      2. 0 < stock <= min_stock               -> Low Stock
      3. stock > min_stock but will run out
         within 7 days at current sale pace   -> Reorder Soon
      4. otherwise                            -> Healthy

    Reorder quantity = enough for 14 days of average sales, topped
    up so it also clears the minimum-stock gap; falls back to
    min_stock when there's no sales history at all.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT product_id, name, category, stock, min_stock FROM products WHERE status = 'Active'")
    products = [dict(r) for r in cur.fetchall()]
    conn.close()

    velocity = get_product_sales_velocity(days)

    table = []
    for p in products:
        recent_sales = velocity.get(p["product_id"], 0)
        avg_daily_sales = recent_sales / days if days > 0 else 0
        days_of_stock_left = (p["stock"] / avg_daily_sales) if avg_daily_sales > 0 else None

        if p["stock"] == 0:
            status = "🔴 Out of Stock"
            reason = "Stock is at zero — sales are being missed right now."
        elif p["stock"] <= p["min_stock"]:
            status = "🟡 Low Stock"
            reason = f"Stock ({p['stock']}) is at or below the minimum level ({p['min_stock']})."
        elif days_of_stock_left is not None and days_of_stock_left <= 7:
            status = "🟠 Reorder Soon"
            reason = (
                f"At the recent pace of {avg_daily_sales:.1f} units/day, current stock "
                f"will last about {days_of_stock_left:.0f} more day(s)."
            )
        else:
            status = "🟢 Healthy"
            reason = "Stock is comfortably above the minimum level for the recent sales pace."

        if status in ("🔴 Out of Stock", "🟡 Low Stock", "🟠 Reorder Soon"):
            velocity_based = round(avg_daily_sales * 14)
            gap_based = max(0, p["min_stock"] - p["stock"])
            recommended_reorder = max(velocity_based, gap_based, p["min_stock"] if recent_sales == 0 else 0)
        else:
            recommended_reorder = 0

        table.append({
            "product_id": p["product_id"],
            "name": p["name"],
            "category": p["category"],
            "stock": p["stock"],
            "min_stock": p["min_stock"],
            "recent_sales": recent_sales,
            "avg_daily_sales": round(avg_daily_sales, 2),
            "status": status,
            "recommended_reorder": recommended_reorder,
            "reason": reason,
        })

    return table


def get_fast_moving_products(limit: int = 5, days: int = 30):
    """Top N active products by units sold in the last `days` days."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT p.product_id, p.name, p.category, SUM(bi.quantity) AS qty_sold
        FROM bill_items bi
        JOIN bills b ON bi.bill_id = b.bill_id
        JOIN products p ON bi.product_id = p.product_id
        WHERE date(b.bill_date) >= date('now', ?) AND p.status = 'Active'
        GROUP BY p.product_id
        ORDER BY qty_sold DESC
        LIMIT ?
    """, (f"-{days} days", limit))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_slow_moving_products(limit: int = 5, days: int = 30):
    """
    Bottom N active products by units sold in the last `days` days,
    including products with zero sales (LEFT JOIN) since those are
    exactly the overstock candidates worth flagging.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT p.product_id, p.name, p.category, p.stock,
               COALESCE(SUM(bi.quantity), 0) AS qty_sold
        FROM products p
        LEFT JOIN bill_items bi ON bi.product_id = p.product_id
        LEFT JOIN bills b ON bi.bill_id = b.bill_id AND date(b.bill_date) >= date('now', ?)
        WHERE p.status = 'Active'
        GROUP BY p.product_id
        ORDER BY qty_sold ASC, p.stock DESC
        LIMIT ?
    """, (f"-{days} days", limit))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

