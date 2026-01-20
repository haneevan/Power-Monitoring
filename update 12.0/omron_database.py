import sqlite3
import os
from datetime import datetime
from collections import namedtuple

# Define the database name
DB_NAME = 'omron.db'

# Structure updated to include val_power_w
# Order: id, timestamp, voltage, current, power, energy, unit_id
Reading = namedtuple('Reading', ['id', 'timestamp', 'val_voltage', 'val_current', 'val_power_w', 'val_energy_kwh', 'unit_id'])

def setup_database():
    """Initializes the database and creates the table with unit support."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Create the readings table with the new Active Power column
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            val_voltage REAL NOT NULL,
            val_current REAL NOT NULL,
            val_power_w REAL NOT NULL,
            val_energy_kwh REAL NOT NULL,
            unit_id TEXT NOT NULL
        )
    ''')
    
    # Preserving your index for performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_unit_timestamp ON readings (unit_id, timestamp)')
    
    conn.commit()
    conn.close()
    print(f"Database initialized: {os.path.abspath(DB_NAME)}")

def log_reading(v, a, p, kwh, unit_id):
    """Saves a measurement including Active Power tagged with the unit ID."""
    timestamp_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        # Updated to insert 6 values (timestamp + 4 metrics + unit_id)
        cursor.execute('''
            INSERT INTO readings (timestamp, val_voltage, val_current, val_power_w, val_energy_kwh, unit_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (timestamp_str, v, a, p, kwh, unit_id))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database Insert Error: {e}")
    finally:
        conn.close()

def get_historical_readings(days=1, unit_id="unit01"):
    """Fetches records for the last X days (Used by Dashboards)."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # SELECT * ensures we get all columns in the order defined in the namedtuple
    query = """
        SELECT * FROM readings 
        WHERE unit_id = ? 
        AND timestamp >= datetime('now', ?, 'localtime') 
        ORDER BY timestamp ASC
    """
    cursor.execute(query, (unit_id, f"-{days} day"))
    rows = cursor.fetchall()
    conn.close()
    return [Reading(*row) for row in rows]

def get_historical_readings_by_range(start_date, end_date, unit_id="unit01", skip=1):
    """Fetches records between two dates with skip support (Used by Hikaku/Comparison)."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Preserving your id % ? downsampling logic
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
    """Deletes old records to prevent the database from growing too large."""
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
