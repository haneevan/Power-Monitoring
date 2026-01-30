import sqlite3
import os
from datetime import datetime
from collections import namedtuple

# Define the database name
DB_NAME = 'omron.db'

# --- UPDATED STRUCTURE (6 Data Fields + ID) ---
# Removed val_power_factor to match your migration
Reading = namedtuple('Reading', [
    'id', 'timestamp', 'val_voltage', 'val_current', 
    'val_power_kw', 'val_energy_kwh', 'unit_id'
])

def setup_database():
    """Initializes the database and creates the table with unit support."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # --- UPDATED TABLE SCHEMA ---
    # Matches the migration: ID, TS, V, A, KW, KWH, UNIT_ID
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            val_voltage REAL NOT NULL,
            val_current REAL NOT NULL,
            val_power_kw REAL NOT NULL,
            val_energy_kwh REAL NOT NULL,
            unit_id TEXT NOT NULL
        )
    ''')
    
    # Performance index for the comparison and history views
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_unit_timestamp ON readings (unit_id, timestamp)')
    
    conn.commit()
    conn.close()
    print(f"Database initialized: {os.path.abspath(DB_NAME)}")

def log_reading(v, a, kw, kwh, unit_id):
    """
    Saves a measurement. 
    Applies ABS() to kW to fix the reversed CT installation issue.
    """
    timestamp_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Manual Correction for Reversed CT
    # We take the absolute value of kW so the energy charts show positive usage.
    fixed_kw = abs(kw)
    
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO readings (
                timestamp, val_voltage, val_current, 
                val_power_kw, val_energy_kwh, unit_id
            )
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (timestamp_str, v, a, fixed_kw, kwh, unit_id))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database Insert Error: {e}")
    finally:
        conn.close()

def get_historical_readings(days=1, unit_id="unit01"):
    """Fetches records for the last X days (Used by Slide 1 and 2)."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    query = """
        SELECT * FROM readings 
        WHERE unit_id = ? 
        AND timestamp >= datetime('now', ?, 'localtime') 
        ORDER BY timestamp ASC
    """
    cursor.execute(query, (unit_id, f"-{days} day"))
    rows = cursor.fetchall()
    conn.close()
    # Unpacks the 7 columns into the Reading namedtuple
    return [Reading(*row) for row in rows]

def get_historical_readings_by_range(start_date, end_date, unit_id="unit01", skip=1):
    """Fetches records for specific dates with downsampling (Used by Hikaku Comparison)."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    query = """
        SELECT * FROM readings 
        WHERE unit_id = ? 
        AND date(timestamp) BETWEEN ? AND ? 
        AND (id % ? = 0)
        ORDER BY timestamp ASC
    """
    try:
        cursor.execute(query, (unit_id, start_date, end_date, skip))
        rows = cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Database Range Error: {e}")
        rows = []
    finally:
        conn.close()
        
    return [Reading(*row) for row in rows]

def cleanup_old_data(days=30):
    """Deletes records older than 30 days to save space on SD card."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM readings WHERE timestamp < datetime('now', ?, 'localtime')", (f"-{days} day",))
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        if deleted_count > 0:
            print(f"Cleanup: Deleted {deleted_count} records older than {days} days.")
    except sqlite3.Error as e:
        print(f"Database Cleanup Error: {e}")

if __name__ == "__main__":
    setup_database()
