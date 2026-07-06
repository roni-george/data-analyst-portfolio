# database.py
import sqlite3

DB_FILE = "ecommerce_store.db"

def init_db():
    """Initializes the database table with exact constraint requirements."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS refund_audits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT,
            customer_email TEXT,
            order_number TEXT,
            item_name TEXT,
            days_since_purchase INTEGER,
            item_condition TEXT,
            customer_reason TEXT,
            audit_status TEXT DEFAULT 'Pending',
            resolution_draft TEXT,
            email_sent_status TEXT
        )
    """)
    conn.commit()
    conn.close()

def insert_new_request(name, email, order, item, days, condition, reason, status='Pending Evaluation', sent_status=None):
    """Logs an initial extraction run, returning the unique row ID."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO refund_audits (
            customer_name, customer_email, order_number, item_name, 
            days_since_purchase, item_condition, customer_reason, audit_status, email_sent_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, email, order, item, days, condition, reason, status, sent_status))
    inserted_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return inserted_id

def get_last_incomplete_record(customer_email):
    """Finds the most recent incomplete file for a responding customer email."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, order_number, item_name, days_since_purchase, item_condition, customer_reason 
        FROM refund_audits 
        WHERE customer_email = ? AND audit_status = 'Incomplete Data'
        ORDER BY id DESC LIMIT 1
    """, (customer_email,))
    record = cursor.fetchone()
    conn.close()
    return record

def update_record(record_id, order, item, days, condition, reason, status, draft, sent_status):
    """Commits final data merges and resolutions back to the database row."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE refund_audits 
        SET order_number = ?, item_name = ?, days_since_purchase = ?, 
            item_condition = ?, customer_reason = ?, audit_status = ?, 
            resolution_draft = ?, email_sent_status = ?
        WHERE id = ?
    """, (order, item, days, condition, reason, status, draft, sent_status, record_id))
    conn.commit()
    conn.close()