import sqlite3
import datetime
import os

DB_FILE = 'inventory.db'

# --- Database Initialization (Keep as is) ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # (Keep table creation queries exactly as before)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            sku TEXT PRIMARY KEY, name TEXT NOT NULL, price REAL NOT NULL CHECK(price >= 0),
            quantity INTEGER NOT NULL CHECK(quantity >= 0) ) ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, total_amount REAL NOT NULL ) ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transaction_items (
            item_id INTEGER PRIMARY KEY AUTOINCREMENT, transaction_id INTEGER NOT NULL,
            product_sku TEXT NOT NULL, quantity_sold INTEGER NOT NULL,
            price_at_sale REAL NOT NULL,
            FOREIGN KEY(transaction_id) REFERENCES transactions(transaction_id),
            FOREIGN KEY(product_sku) REFERENCES products(sku) ON DELETE RESTRICT ) ''') # Added ON DELETE RESTRICT
    conn.commit()
    conn.close()
    # print(f"Database '{DB_FILE}' initialized successfully.") # GUI will handle messages


# --- Database Connection ---
def get_db_connection():
    """Gets a connection to the DB. Remember to close it!"""
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON") # Good practice
    return conn

# --- Product Management (Modified for GUI) ---

def add_product(sku, name, price, quantity):
    """Adds a product. Returns success message or raises error."""
    if not sku or not name or price is None or quantity is None:
        raise ValueError("Missing required product information (SKU, Name, Price, Quantity).")
    if price < 0 or quantity < 0:
        raise ValueError("Price and Quantity cannot be negative.")

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO products (sku, name, price, quantity) VALUES (?, ?, ?, ?)',
                       (sku.strip().upper(), name.strip(), float(price), int(quantity)))
        conn.commit()
        return f"Product '{name}' ({sku}) added."
    except sqlite3.IntegrityError:
        conn.rollback()
        raise ValueError(f"SKU '{sku}' already exists.")
    except ValueError as e: # Catch potential float/int conversion errors too
         conn.rollback()
         raise ValueError(f"Invalid input: {e}")
    except Exception as e:
        conn.rollback()
        raise RuntimeError(f"Database error adding product: {e}") # More generic for other DB issues
    finally:
        conn.close()

def remove_product(sku):
    """Removes a product by SKU. Returns success message or raises error."""
    if not sku:
        raise ValueError("SKU cannot be empty.")

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # Check if product exists first
        cursor.execute('SELECT name FROM products WHERE sku = ?', (sku,))
        product = cursor.fetchone()
        if not product:
            raise ValueError(f"Product with SKU '{sku}' not found.")

        # Attempt deletion
        cursor.execute('DELETE FROM products WHERE sku = ?', (sku,))
        conn.commit()
        # Check if deletion happened (it should if no FK constraints fail)
        if cursor.rowcount == 0:
             # This might happen if it was deleted between the check and now, or due to FK
             raise RuntimeError(f"Could not delete product '{sku}'. It might be referenced in transactions.")
        return f"Product '{product[0]}' ({sku}) removed successfully."
    except sqlite3.IntegrityError as e:
         conn.rollback()
         # This will trigger if ON DELETE RESTRICT is active and the product is in transaction_items
         raise ValueError(f"Cannot remove product '{sku}': It is part of past transactions. ({e})")
    except Exception as e:
        conn.rollback()
        raise RuntimeError(f"Database error removing product: {e}")
    finally:
        conn.close()

def get_all_products():
    """Returns a list of all products as tuples (sku, name, price, quantity)."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT sku, name, price, quantity FROM products ORDER BY name')
        products = cursor.fetchall()
        return products
    except Exception as e:
        raise RuntimeError(f"Database error fetching products: {e}")
    finally:
        conn.close()

def find_products(search_term):
    """Finds products by SKU or Name (case-insensitive). Returns list of tuples."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        search_pattern = f"%{search_term}%"
        cursor.execute('''
            SELECT sku, name, price, quantity
            FROM products
            WHERE sku = ? OR name LIKE ?
            ORDER BY name
        ''', (search_term.strip().upper(), search_pattern))
        return cursor.fetchall()
    except Exception as e:
        raise RuntimeError(f"Database error searching products: {e}")
    finally:
        conn.close()

def get_product_details(sku):
     """Gets details for a single product by SKU."""
     conn = get_db_connection()
     try:
         cursor = conn.cursor()
         cursor.execute('SELECT sku, name, price, quantity FROM products WHERE sku = ?', (sku,))
         return cursor.fetchone() # Returns tuple or None
     except Exception as e:
        raise RuntimeError(f"Database error getting product details: {e}")
     finally:
         conn.close()

# --- Billing (Modified for GUI) ---

def process_sale(bill_items):
    """
    Processes the sale transaction.
    Args: bill_items: List of tuples [(sku, name, price_at_sale, quantity_sold), ...]
    Returns: transaction_id on success
    Raises: ValueError or RuntimeError on failure
    """
    if not bill_items:
        raise ValueError("Cannot process an empty bill.")

    conn = get_db_connection()
    cursor = conn.cursor()
    current_total = sum(item[2] * item[3] for item in bill_items)

    try:
        # Step 1: Create Transaction Record
        cursor.execute('INSERT INTO transactions (total_amount) VALUES (?)', (current_total,))
        transaction_id = cursor.lastrowid

        # Step 2: Add Items to transaction_items and Update Stock
        for sku, name, price_at_sale, quantity_sold in bill_items:
            # Check stock again just before updating (important!)
            cursor.execute('SELECT quantity FROM products WHERE sku = ?', (sku,))
            current_stock = cursor.fetchone()
            if not current_stock or current_stock[0] < quantity_sold:
                 raise ValueError(f"Insufficient stock for '{name}' ({sku}) during final checkout. Only {current_stock[0] if current_stock else 0} left.")

            # Add item to transaction details
            cursor.execute('''
                INSERT INTO transaction_items (transaction_id, product_sku, quantity_sold, price_at_sale)
                VALUES (?, ?, ?, ?)
            ''', (transaction_id, sku, quantity_sold, price_at_sale))

            # Update product stock
            cursor.execute('''
                UPDATE products SET quantity = quantity - ? WHERE sku = ?
            ''', (quantity_sold, sku))
            # No need for rowcount check here as we checked stock above, rely on commit/rollback

        # Step 3: Commit Transaction
        conn.commit()
        return transaction_id

    except Exception as e:
        conn.rollback() # Rollback the transaction
        # Raise a more specific error if possible, otherwise generic
        if isinstance(e, ValueError): # Re-raise our specific stock error
             raise e
        raise RuntimeError(f"Database error during checkout: {e}")
    finally:
        conn.close()


# --- Receipt and History (Modified for GUI) ---

def get_transaction_details(transaction_id):
    """Gets details for receipt printing. Returns (trans_info_tuple, items_list_of_tuples)"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # Get transaction info
        cursor.execute('SELECT transaction_id, timestamp, total_amount FROM transactions WHERE transaction_id = ?', (transaction_id,))
        trans_info = cursor.fetchone()
        if not trans_info:
            raise ValueError(f"Transaction ID {transaction_id} not found.")

        # Get items for this transaction
        cursor.execute('''
            SELECT ti.quantity_sold, p.name, ti.product_sku, ti.price_at_sale
            FROM transaction_items ti
            JOIN products p ON ti.product_sku = p.sku
            WHERE ti.transaction_id = ?
        ''', (transaction_id,))
        items = cursor.fetchall() # List of (qty, name, sku, price) tuples
        return trans_info, items
    except Exception as e:
        raise RuntimeError(f"Database error fetching transaction details: {e}")
    finally:
        conn.close()


def get_transaction_history(limit=50):
    """Returns a list of recent transactions as tuples (id, timestamp, total)."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT transaction_id, timestamp, total_amount
            FROM transactions
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))
        return cursor.fetchall()
    except Exception as e:
        raise RuntimeError(f"Database error fetching transaction history: {e}")
    finally:
        conn.close()

# --- Initialize DB on first import/run if needed ---
if not os.path.exists(DB_FILE):
     print(f"Database file '{DB_FILE}' not found. Initializing...")
     try:
         init_db()
         print("Database initialized successfully.")
     except Exception as e:
         print(f"FATAL ERROR: Could not initialize database: {e}")
         # In a GUI app, you might show an error dialog and exit here
         exit() # Exit if DB init fails critically